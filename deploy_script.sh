#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  LifeLine – EC2 deploy (Amazon Linux 2023) – FINAL VERSION
# ─────────────────────────────────────────────────────────────
#  Required env-vars: HOSTNAME, DJANGO_SECRET_KEY, OPENAI_API_KEY
#  Optional: LETSENCRYPT_EMAIL  (defaults to admin@HOSTNAME)
# ─────────────────────────────────────────────────────────────
set -euo pipefail

: "${HOSTNAME:?HOSTNAME not set}"
: "${DJANGO_SECRET_KEY:?DJANGO_SECRET_KEY not set}"
: "${OPENAI_API_KEY:?OPENAI_API_KEY not set}"
LE_EMAIL="${LETSENCRYPT_EMAIL:-admin@${HOSTNAME}}"
WWW_HOST="www.${HOSTNAME}"

echo ">>> Deploying LifeLine → ${HOSTNAME}"

# 1. Stop services
sudo systemctl stop lifeline-backend || true
sudo systemctl stop nginx           || true

# 2. OS packages
sudo yum install -y python3-pip certbot bind-utils rsync

# 3. Sync application files
sudo mkdir -p /home/ec2-user/lifeline/{backend,frontend}
sudo rsync -a --delete /tmp/backend/        /home/ec2-user/lifeline/backend/
sudo rsync -a --delete /tmp/frontend_build/ /home/ec2-user/lifeline/frontend/
sudo chmod 755 /home/ec2-user /home/ec2-user/lifeline
sudo chmod -R 755 /home/ec2-user/lifeline/frontend

# 4. Python venv & deps
cd /home/ec2-user/lifeline
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
pip install --upgrade gunicorn

# 5. Django migrate & collectstatic
cd /home/ec2-user/lifeline/backend/LifeLine
export DJANGO_SECRET_KEY OPENAI_API_KEY
python manage.py migrate
python manage.py collectstatic --noinput

# 6. systemd unit for Gunicorn
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

# 7. Write the ONLY Nginx vhost (HTTP + HTTPS) – never touched again
sudo tee /etc/nginx/conf.d/lifeline.conf >/dev/null <<EOF
server {
    listen 80;
    server_name ${HOSTNAME} ${WWW_HOST};
    root /home/ec2-user/lifeline/frontend;
    location /.well-known/acme-challenge/ { root /var/www/html; }
    location / { return 301 https://\$host\$request_uri; }
}

server {
    listen 443 ssl;
    http2  on;
    server_name ${HOSTNAME} ${WWW_HOST};

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
    }
}
EOF
sudo nginx -t
sudo systemctl restart nginx   # start HTTP so ACME challenge works

# 8. Ensure DNS → this EC2
PUB_IP=$(curl -s http://checkip.amazonaws.com/)
for R in 8.8.8.8 1.1.1.1; do
  if [[ $(dig +short "${HOSTNAME}" @$R | head -n1) != "$PUB_IP" ]]; then
    echo "DNS not propagated to ${PUB_IP}. Abort."; exit 1; fi
done

# 9. Obtain / renew cert *without* editing Nginx
sudo certbot certonly \
     --webroot -w /var/www/html \
     -d "${HOSTNAME}" -d "${WWW_HOST}" \
     --non-interactive --agree-tos --email "${LE_EMAIL}" \
     --deploy-hook "systemctl reload nginx"

# 10. Enable auto-renew (already reloads via deploy-hook)
sudo systemctl enable --now certbot-renew.timer

# 11. Start backend & reload Nginx
sudo systemctl daemon-reload
sudo systemctl enable lifeline-backend
sudo systemctl restart lifeline-backend
sudo systemctl reload nginx

# 12. Health check
curl -skf https://${HOSTNAME}/api/healthz >/dev/null
echo ">>> Deployment successful 🎉"
