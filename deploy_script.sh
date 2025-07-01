#!/bin/bash
# This script is executed on the EC2 instance to deploy the LifeLine application.
set -e

# Environment variables need to be exported by the calling process (GitHub Actions)
# Required: HOSTNAME, DJANGO_SECRET_KEY, OPENAI_API_KEY

# --- 1. Stop services and clean up previous deployment ---
echo "--- Stopping services and cleaning up ---"
sudo systemctl stop lifeline-backend || true
sudo systemctl stop nginx || true
sudo rm -rf /home/ec2-user/lifeline
mkdir -p /home/ec2-user/lifeline/backend
mkdir -p /home/ec2-user/lifeline/frontend

# --- 2. Move new application files into place ---
echo "--- Moving new application files ---"
sudo mv /tmp/backend/* /home/ec2-user/lifeline/backend/
sudo mv /tmp/frontend_build/* /home/ec2-user/lifeline/frontend/
sudo chmod 755 /home/ec2-user /home/ec2-user/lifeline
sudo chmod -R 755 /home/ec2-user/lifeline/frontend

# --- 3. Install Python dependencies ---
echo "--- Installing Python dependencies ---"
cd /home/ec2-user/lifeline
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
pip install gunicorn

# --- 4. Setup Django ---
echo "--- Setting up Django database ---"
cd /home/ec2-user/lifeline/backend/LifeLine
python manage.py migrate
python manage.py collectstatic --noinput

# --- 5. Create systemd environment file ---
echo "--- Creating systemd environment file ---"
# Read secrets from temporary files to avoid shell interpretation issues
DJANGO_SECRET_KEY=$(cat /tmp/django_secret_key)
OPENAI_API_KEY=$(cat /tmp/openai_api_key)

echo "DJANGO_SECRET_KEY=$DJANGO_SECRET_KEY" | sudo tee /etc/lifeline.env
echo "OPENAI_API_KEY=$OPENAI_API_KEY" | sudo tee -a /etc/lifeline.env
sudo chmod 644 /etc/lifeline.env

# Clean up temporary secret files
sudo rm /tmp/django_secret_key /tmp/openai_api_key

# --- 6. Create systemd service file ---
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
ExecStart=/home/ec2-user/lifeline/venv/bin/gunicorn LifeLine.wsgi:application --bind 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
EOT

# --- 7. Configure Nginx and SSL with Certbot ---
echo "--- Configuring Nginx and SSL ---"


sudo yum install -y python3-pip certbot-nginx

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

# Create a temporary Nginx config for Certbot to perform validation
sudo tee /etc/nginx/conf.d/lifeline.conf > /dev/null <<EOT
server {
    listen 80;
    server_name $HOSTNAME;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        return 404; # Return 404 for all other requests during validation
    }
}
EOT

sudo mkdir -p /var/www/html
sudo systemctl restart nginx || sudo systemctl start nginx
sleep 5 # Give Nginx a moment to start

# Obtain the SSL certificate from Let's Encrypt
echo "--- Obtaining SSL certificate from Let's Encrypt ---"
sudo certbot --nginx -d $HOSTNAME --non-interactive --agree-tos --email admin@lifeline.com --redirect

# Certbot automatically creates the final Nginx config. We just need to ensure it's correct.
# The final config will handle HTTPS and proxying to the Django app.

# --- 8. Start all services ---
echo "--- Starting all services ---"
sudo systemctl daemon-reload
sudo systemctl restart nginx
sudo systemctl enable lifeline-backend
sudo systemctl start lifeline-backend

echo "--- Deployment successful! ---"

# --- 9. Final Health Check ---
echo "--- Performing Final Health Checks ---"
echo "--- Nginx Status ---"
sudo systemctl status nginx --no-pager || echo "Nginx failed to start"
echo "--- Backend Status ---"
sudo systemctl status lifeline-backend --no-pager || echo "Backend failed to start"
echo "--- Listening Ports ---"
sudo netstat -tulpn | grep LISTEN
echo "--- Nginx Configuration Test ---"
sudo nginx -t
echo "--- Last 30 lines of Nginx Error Log ---"
sudo tail -n 30 /var/log/nginx/error.log || echo "No Nginx error log found."
echo "--- Last 30 lines of Backend Log ---"
sudo journalctl -u lifeline-backend -n 30 --no-pager || echo "No backend log found."
