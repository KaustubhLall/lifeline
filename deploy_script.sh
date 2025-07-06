#!/usr/bin/env bash
set -euo pipefail

# ─── 0. CONFIG ──────────────────────────────────────────────────────────
: "${HOSTNAME:?HOSTNAME not set}"
: "${DJANGO_SECRET_KEY:?secret key missing}"
: "${OPENAI_API_KEY:?openai key missing}"
LE_EMAIL="${LETSENCRYPT_EMAIL:-admin@${HOSTNAME}}"
WWW="www.${HOSTNAME}"

# ─── 1. STOP SERVICES ───────────────────────────────────────────────────
sudo systemctl stop lifeline-backend || true
sudo systemctl stop nginx            || true

# ─── 2. DEPENDENCIES (curl/openssl already present)──────────────────────
sudo yum install -y python3-pip certbot bind-utils rsync

# ─── 3. SYNC APP FILES ──────────────────────────────────────────────────
sudo mkdir -p /home/ec2-user/lifeline/{backend,frontend}

# Backup existing database if it exists
if [ -f "/home/ec2-user/lifeline/backend/LifeLine/db.sqlite3" ]; then
    echo "Backing up existing database..."
    sudo cp /home/ec2-user/lifeline/backend/LifeLine/db.sqlite3 /home/ec2-user/lifeline/db.sqlite3.backup
fi

# Sync backend files but exclude the database
sudo rsync -a --delete --exclude='LifeLine/db.sqlite3' /tmp/backend/ /home/ec2-user/lifeline/backend/

# Restore database backup if no database exists after sync
if [ ! -f "/home/ec2-user/lifeline/backend/LifeLine/db.sqlite3" ] && [ -f "/home/ec2-user/lifeline/db.sqlite3.backup" ]; then
    echo "Restoring database from backup..."
    sudo cp /home/ec2-user/lifeline/db.sqlite3.backup /home/ec2-user/lifeline/backend/LifeLine/db.sqlite3
fi

# Sync frontend files (no database concerns here)
sudo rsync -a --delete /tmp/frontend_build/ /home/ec2-user/lifeline/frontend/
sudo chmod -R 755 /home/ec2-user/lifeline/frontend

# ─── 4. PYTHON VENV ─────────────────────────────────────────────────────
cd /home/ec2-user/lifeline
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt gunicorn

# ─── 5. DJANGO ──────────────────────────────────────────────────────────
cd backend/LifeLine
export DJANGO_SECRET_KEY OPENAI_API_KEY
python manage.py migrate
python manage.py collectstatic --noinput

# Create superuser if it doesn't exist
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser('admin', 'admin@lifeline.com', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
"

# ─── 6. systemd SERVICE ─────────────────────────────────────────────────
sudo tee /etc/lifeline.env >/dev/null <<EOF
DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
OPENAI_API_KEY=${OPENAI_API_KEY}
EOF
sudo chmod 644 /etc/lifeline.env

sudo tee /etc/systemd/system/lifeline-backend.service >/dev/null <<'EOF'
[Unit]
Description=LifeLine Django Backend
After=network.target
[Service]
User=ec2-user
EnvironmentFile=/etc/lifeline.env
WorkingDirectory=/home/ec2-user/lifeline/backend/LifeLine
ExecStart=/home/ec2-user/lifeline/venv/bin/gunicorn LifeLine.wsgi:application \
          --bind 0.0.0.0:8000 --log-level warning
Restart=always
[Install]
WantedBy=multi-user.target
EOF

# ─── 7. SINGLE NGINX VHOST  (never edited again) ───────────────────────
sudo rm -f /etc/nginx/conf.d/lifeline.conf
sudo tee /etc/nginx/conf.d/lifeline.conf >/dev/null <<EOF

server {
    listen 80;
    server_name ${HOSTNAME} ${WWW};
    root /home/ec2-user/lifeline/frontend;
    location /.well-known/acme-challenge/ { root /var/www/html; }
    location / { return 301 https://\$host\$request_uri; }
}
server {
    listen 443 ssl;
    http2 on;
    server_name ${HOSTNAME} ${WWW};
    ssl_certificate     /etc/letsencrypt/live/${HOSTNAME}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${HOSTNAME}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    root /home/ec2-user/lifeline/frontend;
    index index.html;
    location / { try_files \$uri /index.html; }
    location /static/ {
        alias /home/ec2-user/lifeline/frontend/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    location /admin {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Port \$server_port;

        # CSRF and session handling
        proxy_cookie_path / /;
        proxy_cookie_domain ~ \$host;
        proxy_redirect off;
    }
}
EOF
sudo nginx -t
sudo systemctl start nginx   # for ACME challenge

# ─── 8. DNS CHECK & UPDATE ──────────────────────────────────────────────
PUB=$(curl -s http://checkip.amazonaws.com/)
echo "Current EC2 public IP: $PUB"

# Update DuckDNS record if DUCKDNS_TOKEN is available
if [[ -n "${DUCKDNS_TOKEN:-}" ]]; then
  echo "Updating DuckDNS record..."
  DUCKDNS_DOMAIN=$(echo "$HOSTNAME" | sed 's/\.duckdns\.org$//')
  curl -s "https://www.duckdns.org/update?domains=${DUCKDNS_DOMAIN}&token=${DUCKDNS_TOKEN}&ip=${PUB}"
  echo "DuckDNS update completed"

  # Wait a moment for DNS propagation
  sleep 10
fi

# Check DNS resolution
for R in 8.8.8.8 1.1.1.1; do
  A=$(dig +short "${HOSTNAME}" @$R | head -n1)
  echo "DNS server $R resolves $HOSTNAME to: $A"
  echo "Expected IP: $PUB"

  if [[ "$A" != "$PUB" ]]; then
    echo "DNS $R not ready - resolved IP ($A) doesn't match EC2 IP ($PUB)"
    echo "Please update your DuckDNS record manually or add DUCKDNS_TOKEN to secrets"
    exit 1
  fi
done
echo "DNS check passed"

# ─── 9. CERTBOT (fetch only, no nginx edits) ────────────────────────────
sudo certbot certonly -n --agree-tos -m "$LE_EMAIL" \
     --webroot -w /var/www/html \
     -d "$HOSTNAME" -d "$WWW" \
     --deploy-hook "systemctl reload nginx"

# ─── 10. VERIFY / FIX CONFIG (one last time) ────────────────────────────
sudo sed -i -E "
  s/\\\$?HOSTNAME/${HOSTNAME//\//\\/}/g;
  s/^( *listen[[:space:]]+443[[:space:]]+ssl)[[:space:]]+http2;/\1;/;
  /http2 on;/d
" /etc/nginx/conf.d/lifeline.conf
sudo sed -i -E '/listen[[:space:]]+443[[:space:]]+ssl;/a\    http2 on;' \
    /etc/nginx/conf.d/lifeline.conf
if grep -qE '\$HOSTNAME|listen[[:space:]]+443[[:space:]]+ssl[[:space:]]+http2;' \
   /etc/nginx/conf.d/lifeline.conf; then
   echo "fatal: config still wrong"; exit 1; fi

sudo nginx -t && sudo systemctl reload nginx

# ─── 11. ENABLE AUTO-RENEW & BACKEND ────────────────────────────────────
sudo systemctl enable --now certbot-renew.timer
sudo systemctl daemon-reload
sudo systemctl enable --now lifeline-backend

# ─── 12. HEALTH CHECK ──────────────────────────────────────────────────
curl -skf https://${HOSTNAME}/ || { echo "Health-check failed"; exit 1; }
echo ">>> Deployment finished without warnings 🎉"
