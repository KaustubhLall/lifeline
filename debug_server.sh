#!/bin/bash
# Debug script to check server status

echo "=== 1. Check what files are in frontend directory ==="
ls -la /home/ec2-user/lifeline/frontend/

echo -e "\n=== 2. Check if index.html exists and its content ==="
if [ -f /home/ec2-user/lifeline/frontend/index.html ]; then
    echo "index.html exists:"
    head -10 /home/ec2-user/lifeline/frontend/index.html
else
    echo "index.html does NOT exist!"
fi

echo -e "\n=== 3. Test Django API directly ==="
curl -s http://localhost:8000/api/health/ || echo "Django API failed"

echo -e "\n=== 4. Test what nginx returns for root ==="
curl -v http://localhost/ 2>&1 | head -20

echo -e "\n=== 5. Check nginx error logs ==="
sudo tail -20 /var/log/nginx/error.log

echo -e "\n=== 6. Check nginx access logs ==="
sudo tail -10 /var/log/nginx/access.log

echo -e "\n=== 7. Check permissions ==="
ls -la /home/ec2-user/lifeline/

echo -e "\n=== 8. Test direct file access ==="
curl -I http://localhost/index.html

echo -e "\n=== 9. Check nginx process and config ==="
sudo nginx -t
ps aux | grep nginx
