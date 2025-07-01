#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  LifeLine – one-shot deploy on Amazon Linux 2023
#  • Assumes frontend build in /tmp/frontend_build/
#  • Assumes backend code   in /tmp/backend/
#  • Requires these env-vars (exported by caller / GitHub Actions):
#      HOSTNAME           lifeline-kaus.duckdns.org        (DNS already → EC2 IP)
#      DJANGO_SECRET_KEY  <secret>
#      OPENAI_API_KEY     <secret>
#    Optional:
#      LETSENCRYPT_EMAIL  you@example.com   (defaults to admin@${HOSTNAME})
# ─────────────────────────────────────────────────────────────
set -euo pipefail

# ─┐ 0. Validate env-vars
# ─┴───────────────────────────────────────────────────────────
: "${HOSTNAME:?HOSTNAME not set}"
: "${DJANGO_SECRET_KEY:?DJANGO_SECRET_KEY not set}"
: "${OPENAI_API_KEY:?OPENAI_API_KEY not set}"
LE_EMAIL="${LETSENCRYPT_EMAIL:-admin@${HOSTNAME}}"

echo ">>> Deploying LifeLine to ${HOSTNAME}"

# ─┐ 1. Stop running services (ignore if absent)
# ─┴───────────────────────────────────────────────────────────
sudo systemctl stop lifeline-backend || true
sudo systemctl stop nginx           || true

# ─┐ 2. OS packages
# ─┴───────────────────────────────────────────────────────────
sudo yum install -y python3-pip certbot-nginx bind-utils rsync curl openssl

# ─┐ 3. Sync application files
# ─┴───────────────────────────────────────────────────────────
sudo mkdir -p /home/ec2-user/lifeline/{backend,frontend}
sudo rsync -a --delete /tmp/backend/        /home/ec2-user/lifeline/backend/
sudo rsync -a --delete /tmp/frontend_build/ /home/ec2-user/lifeline/frontend/
sudo chmod 755 /home/ec2-user /home/ec2-user/lifeline
sudo chmod -R 755 /home/ec2-user/lifeline/frontend

# ─┐ 4. Python virtual-env & deps (re-create each run)
# ─┴───────────────────────────────────────────────────────────
cd /home/ec2-user/lifeline
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
pip install --upgrade gunicorn

# ─┐ 5. Django migrate + collectstatic
# ─┴───────────────────────────────────────────────────────────
cd /home/ec2-user/lifeline/backend/LifeLine
export DJANGO_SECRET_KEY OPENAI_API_KEY
python manage.py migrate
python manage.py collectstatic --noinput

# ─┐ 6. systemd unit for Gunicorn
# ─┴───────────────────────────────────────────────────────────
sudo tee /etc/lifeline.env >/dev/null <<EOF
DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}
OPENAI_API_KEY=${OPENAI_API_KEY}
EOF
sudo chmod 640 /etc/lifeline.env

sudo tee /etc/systemd/system/lifeline-backend.service >/dev/null <<'EOF'
[Unit]
Description=LifeLine Django Backend
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/lifeline/backend/LifeLine
EnvironmentFile=/etc/lifeline.env
ExecStart=/home/ec2-user/lifeline/venv/bin/gunicorn LifeLine.wsgi:application \
          --bind 0.0.0.0:8000 --log-level warning
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# ─┐ 7. HTTP-only Nginx vhost (needed for certbot)
# ─┴───────────────────────────────────────────────────────────
sudo tee /etc/nginx/conf.d/lifeline.conf >/dev/null <<EOF
server {
    listen 80;
    server_name ${HOSTNAME};

    location /.well-known/acme-challenge/ { root /var/www/html; }

    root /home/ec2-user/lifeline/frontend;
    index index.html;

    location /         { try_files \$uri /index.html; }
    location /api      {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# ─┐ 8. DNS points to this EC2?
# ─┴───────────────────────────────────────────────────────────
PUB_IP=$(curl -s http://checkip.amazonaws.com/)
GOOGLE=$(dig +short "${HOSTNAME}" @8.8.8.8 | head -n1)
CFDNS=$(dig +short "${HOSTNAME}" @1.1.1.1 | head -n1)
if [[ "$PUB_IP" != "$GOOGLE" || "$PUB_IP" != "$CFDNS" ]]; then
  echo "DNS for ${HOSTNAME} has not propagated to ${PUB_IP}. Abort."
  exit 1
fi

# ─┐ 9. Start Nginx for HTTP auth-challenge
# ─┴───────────────────────────────────────────────────────────
sudo systemctl restart nginx

# ─┐10. Clean any placeholder certs and re-issue real one
# ─┴───────────────────────────────────────────────────────────
sudo rm -rf /etc/letsencrypt/live/\$HOSTNAME \
            /etc/letsencrypt/archive/\$HOSTNAME 2>/dev/null || true
sudo certbot delete --cert-name '$HOSTNAME' 2>/dev/null || true

sudo certbot --nginx \
     -d "${HOSTNAME}"                                  \
     --non-interactive --agree-tos --email "${LE_EMAIL}" \
     --redirect --force-renewal

# ─┐11. Final HTTPS vhost (overwrites file, variables expand)
# ─┴───────────────────────────────────────────────────────────
sudo tee /etc/nginx/conf.d/lifeline.conf >/dev/null <<EOF
# Redirect HTTP → HTTPS
server {
    listen 80;
    server_name ${HOSTNAME};
    return 301 https://\$host\$request_uri;
}

# HTTPS
server {
    listen 443 ssl;
    http2  on;

    server_name ${HOSTNAME};

    ssl_certificate     /etc/letsencrypt/live/${HOSTNAME}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${HOSTNAME}/privkey.pem;

    ssl_session_cache   shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;

    root /home/ec2-user/lifeline/frontend;
    index index.html;

    location / { try_files \$uri /index.html; }

    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Ssl on;
    }
}
EOF

# ─┐12. Sanitise any stray configs & syntax-check
# ─┴───────────────────────────────────────────────────────────
sudo rm -f /etc/nginx/conf.d/*-le-ssl.conf /etc/nginx/conf.d/*.save
sudo sed -Ei 's#listen[[:space:]]+443[[:space:]]+ssl[[:space:]]+http2;#listen 443 ssl;\n    http2 on;#' \
       /etc/nginx/conf.d/lifeline.conf

sudo nginx -t

# ─┐13. Enable certbot auto-renew
# ─┴───────────────────────────────────────────────────────────
sudo systemctl enable --now certbot-renew.timer

# ─┐14. Start backend & reload Nginx
# ─┴───────────────────────────────────────────────────────────
sudo systemctl daemon-reload
sudo systemctl enable lifeline-backend
sudo systemctl restart lifeline-backend
sudo systemctl reload nginx

# ─┐15. Health check
# ─┴───────────────────────────────────────────────────────────
echo ">>> Verifying HTTPS endpoint"
curl -skf https://"${HOSTNAME}"/api/healthz >/dev/null && \
echo "Deployment successful 🎉"

