#!/bin/bash
# This script is executed on the EC2 instance to deploy the LifeLine application.
set -e

# Environment variables need to be exported by the calling process (GitHub Actions)
# Required: HOSTNAME, DJANGO_SECRET_KEY, OPENAI_API_KEY

# --- 1. Stop services and clean up previous deployment ---
echo "--- Stopping services and cleaning up ---"
sudo systemctl stop lifeline-backend || true
sudo systemctl stop nginx || true

# --- 2. Install required dependencies ---
echo "--- Installing required dependencies ---"
sudo yum install -y python3-pip certbot-nginx bind-utils

# --- 3. Setup application directories ---
echo "--- Setting up application directories ---"
mkdir -p /home/ec2-user/lifeline/backend
mkdir -p /home/ec2-user/lifeline/frontend

# Use rsync instead of mv for better reliability
echo "--- Moving new application files ---"
sudo rsync -a --delete /tmp/backend/ /home/ec2-user/lifeline/backend/
sudo rsync -a --delete /tmp/frontend_build/ /home/ec2-user/lifeline/frontend/
sudo chmod 755 /home/ec2-user /home/ec2-user/lifeline
sudo chmod -R 755 /home/ec2-user/lifeline/frontend

# --- 4. Install Python dependencies ---
echo "--- Installing Python dependencies ---"
cd /home/ec2-user/lifeline
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
pip install gunicorn

# --- 5. Setup Django ---
echo "--- Setting up Django database ---"
cd /home/ec2-user/lifeline/backend/LifeLine

# Read secrets from temporary files and export them for manage.py
export DJANGO_SECRET_KEY=$(cat /tmp/django_secret_key)
export OPENAI_API_KEY=$(cat /tmp/openai_api_key)

python manage.py migrate
python manage.py collectstatic --noinput

# --- 6. Create systemd environment file ---
echo "--- Creating systemd environment file ---"
# Use the same secrets that were just exported
echo "DJANGO_SECRET_KEY=$DJANGO_SECRET_KEY" | sudo tee /etc/lifeline.env
echo "OPENAI_API_KEY=$OPENAI_API_KEY" | sudo tee -a /etc/lifeline.env
sudo chmod 644 /etc/lifeline.env

# Clean up temporary secret files
sudo rm /tmp/django_secret_key /tmp/openai_api_key

# --- 7. Create systemd service file with improved logging configuration ---
echo "--- Creating systemd service file ---"
sudo tee /etc/systemd/system/lifeline-backend.service > /dev/null <<EOT
[Unit]
Description=LifeLine Django Backend
After=network.target

[Service]
Type=simple
User=ec2-user
WorkingDirectory=/home/ec2-user/lifeline/backend/LifeLine
EnvironmentFile=/etc/lifeline.env
ExecStart=/home/ec2-user/lifeline/venv/bin/gunicorn LifeLine.wsgi:application --bind 0.0.0.0:8000 --log-level warning
Restart=always

[Install]
WantedBy=multi-user.target
EOT

# --- 8. Configure Nginx and SSL with Certbot ---
echo "--- Configuring Nginx and SSL ---"

# Create initial HTTP-only Nginx configuration
echo "--- Creating initial HTTP Nginx configuration ---"
sudo tee /etc/nginx/conf.d/lifeline.conf > /dev/null <<EOT
server {
    listen 80;
    server_name $HOSTNAME;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # Root for React frontend
    root /home/ec2-user/lifeline/frontend;
    index index.html;

    # Handle React routing
    location / {
        try_files \$uri /index.html;
    }

    # Proxy API requests to Django backend
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOT

# Add a DNS propagation check before running Certbot
echo "--- Verifying DNS Propagation for Let's Encrypt ---"
PUBLIC_IP=$(curl -s http://checkip.amazonaws.com/)
RESOLVED_IP=$(dig +short $HOSTNAME @8.8.8.8)

echo "This Server's Public IP: $PUBLIC_IP"
echo "Domain ($HOSTNAME) resolves to (via Google DNS): $RESOLVED_IP"

if [ "$PUBLIC_IP" != "$RESOLVED_IP" ]; then
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    echo "!!! DNS VALIDATION FAILED"
    echo "!!! Let's Encrypt will fail because your domain ($HOSTNAME) is not pointing to this server's IP ($PUBLIC_IP)."
    echo "!!! DNS is currently pointing to: $RESOLVED_IP"
    echo "!!! Please wait 10-15 more minutes for DNS to propagate and run the deployment again."
    echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    exit 1
fi

echo "--- DNS Propagation Verified ---"
sudo mkdir -p /var/www/html
sudo chmod -R 755 /var/www/html

# Start Nginx to handle HTTP requests first
echo "--- Starting Nginx with HTTP configuration ---"
sudo systemctl restart nginx || sudo systemctl start nginx
sleep 5 # Give Nginx a moment to start

# Verify Nginx is running before continuing
if ! sudo systemctl is-active --quiet nginx; then
    echo "!!! Nginx failed to start with the HTTP configuration"
    sudo systemctl status nginx --no-pager
    sudo nginx -t
    exit 1
fi

# Create the deploy hook script to fix Certbot's Nginx config updates
echo "--- Creating Certbot deploy hook ---"
sudo tee /etc/letsencrypt/renewal-hooks/deploy/fix-nginx-config.sh > /dev/null <<EOT
#!/bin/bash
# This script fixes the Nginx config after certificate renewal
sed -i 's/listen .* ssl http2;/listen 443 ssl;\n    http2 on;/g' /etc/nginx/conf.d/lifeline.conf
systemctl reload nginx
EOT
sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/fix-nginx-config.sh

# Obtain the SSL certificate from Let's Encrypt
echo "--- Obtaining SSL certificate from Let's Encrypt ---"
sudo mkdir -p /etc/letsencrypt/renewal-hooks/deploy
sudo certbot --nginx -d $HOSTNAME --non-interactive --agree-tos --email admin@lifeline.com --redirect

# Verify the certificate was obtained correctly
if [ ! -f "/etc/letsencrypt/live/$HOSTNAME/fullchain.pem" ] || [ ! -f "/etc/letsencrypt/live/$HOSTNAME/privkey.pem" ]; then
    echo "!!! SSL Certificate files were not created properly"
    ls -la /etc/letsencrypt/live/$HOSTNAME/ || echo "Directory not found"
    sudo cat /var/log/letsencrypt/letsencrypt.log | tail -n 50
    exit 1
fi

# Verify permissions on certificate files
echo "--- Verifying SSL certificate permissions ---"
sudo ls -la /etc/letsencrypt/live/$HOSTNAME/
sudo ls -la /etc/letsencrypt/archive/$HOSTNAME/

# Ensure nginx has access to certificates
echo "--- Ensuring Nginx has access to certificates ---"
sudo chmod -R 755 /etc/letsencrypt/archive
sudo chmod -R 755 /etc/letsencrypt/live

# Fix any HTTP/2 directive issues in the Nginx config
echo "--- Fixing HTTP/2 directive in Nginx config ---"
sudo sed -i 's/listen .* ssl http2;/listen 443 ssl;\n    http2 on;/g' /etc/nginx/conf.d/lifeline.conf

# Create a clean, updated Nginx configuration
echo "--- Creating final Nginx configuration ---"
sudo tee /etc/nginx/conf.d/lifeline.conf > /dev/null <<EOT
# HTTP server - redirect to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name $HOSTNAME;

    # Redirect all HTTP requests to HTTPS
    location / {
        return 301 https://\$host\$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    http2 on;  # Proper way to enable HTTP/2

    server_name $HOSTNAME;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/$HOSTNAME/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$HOSTNAME/privkey.pem;

    # Include SSL options
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_ciphers "ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384";

    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;

    # Root for React frontend
    root /home/ec2-user/lifeline/frontend;
    index index.html;

    # Handle React routing
    location / {
        try_files \$uri /index.html;
    }

    # Proxy API requests to Django backend
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Ssl on;
    }
}
EOT

# Test Nginx configuration
echo "--- Testing Nginx configuration ---"
sudo nginx -t

# Enable the Certbot renewal timer
echo "--- Enabling Certbot renewal timer ---"
sudo systemctl enable --now certbot-renew.timer

# --- 9. Start all services ---
echo "--- Starting all services ---"
sudo systemctl daemon-reload
sudo systemctl enable lifeline-backend
sudo systemctl start lifeline-backend
sudo systemctl restart nginx

echo "--- Deployment successful! ---"

# --- 10. Final Health Check ---
echo "--- Performing Final Health Checks ---"
echo "--- Nginx Status ---"
sudo systemctl status nginx --no-pager || echo "Nginx failed to start"
echo "--- Backend Status ---"
sudo systemctl status lifeline-backend --no-pager || echo "Backend failed to start"
echo "--- Listening Ports ---"
sudo ss -tulpn | grep -E ':80|:443|:8000' || echo "No expected ports found"
echo "--- Nginx Configuration Test ---"
sudo nginx -t
echo "--- Testing SSL Connection ---"
echo | openssl s_client -connect localhost:443 -servername $HOSTNAME 2>/dev/null | grep "Verify return code"
echo "--- SSL Certificate Info ---"
echo | openssl s_client -connect localhost:443 -servername $HOSTNAME 2>/dev/null | openssl x509 -noout -dates
echo "--- Certificate Validity Check ---"
sudo certbot certificates --domain "$HOSTNAME" || echo "Could not check certificate validity"
echo "--- Last 30 lines of Nginx Error Log ---"
sudo tail -n 30 /var/log/nginx/error.log | grep -v 'http2" directive is deprecated' || echo "No Nginx error log found or no errors."
echo "--- Last 30 lines of Backend Log ---"
sudo journalctl -u lifeline-backend -n 30 --no-pager | grep -v "Worker .* was sent SIGTERM" || echo "No backend log found or no errors."
