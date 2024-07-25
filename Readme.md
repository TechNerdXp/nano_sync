# Google Sheets Data Copier

This project provides a Python script to copy data from one Google Sheet to another using the `gspread` and `oauth2client` libraries.

## Setup Instructions

### 1. Create and Activate Virtual Environment

#### On Windows
```bash
python -m venv venv
venv\Scripts\activate

sudo systemctl restart nginx

sudo systemctl reload nginx
sudo systemctl daemon-reload
sudo systemctl restart nano_sync
sudo systemctl enable nano_sync


# script for above 4 commands 
sudo bash /var/www/nano_sync/update_and_restart_services.sh

sudo apt-get install redis-server
sudo service redis-server start
sudo service redis-server restart

sudo apt-get install redis-server
sudo service rabbitmq-server start
sudo service rabbitmq-server restart





# Change ownership to www-data
sudo chown -R www-data:www-data /var/www/nano_sync

# Set permissions
sudo chmod -R 755 /var/www/nano_sync



sudo nano /etc/systemd/system/nano_sync.service

#stop service 

sudo systemctl stop nano_sync

sudo systemctl reload nginx

sudo systemctl status nano_sync.service



"# nano_sync" 


/etc/systemd/system/nano_sync.service

Flask Application Setup with Gunicorn and Nginx

This guide provides step-by-step instructions on setting up a Flask application using Gunicorn as the WSGI HTTP server and Nginx as the web server and reverse proxy. It includes detailed installation, configuration, and running procedures, along with essential debugging tips.

Requirements

Python 3.x
pip
virtualenv (optional, but recommended)
Installation

Flask and Gunicorn

Create and activate a virtual environment (optional):
python3 -m venv myenv
source myenv/bin/activate

Install Flask and Gunicorn:
pip install Flask gunicorn

Nginx

Install Nginx:
For Ubuntu:
sudo apt update
sudo apt install nginx
For CentOS:
sudo yum install epel-release
sudo yum install nginx
Configuration

Gunicorn

Create a Gunicorn systemd service file (nano_sync.service) at /etc/systemd/system:
[Unit]
Description=Gunicorn instance to serve the application
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/nano_sync
ExecStart=/usr/local/bin/gunicorn --workers 3 --timeout 28800 --reload --bind unix:/var/www/nano_sync/nano_sync.sock -m 007 --access-logfile /var/www/nano_sync/access.log --error-logfile /var/www/nano_sync/error.log wsgi

[Install]
WantedBy=multi-user.target

Nginx

Configure Nginx to proxy requests to the Gunicorn socket:
Edit or create a new configuration file in /etc/nginx/sites-available/ and symlink it to /etc/nginx/sites-enabled/.

Example configuration:
server {
listen 80;
server_name yourdomain.com;

bash
Copy code
location /nano_sync {
    proxy_pass http://unix:/var/www/nano_sync/nano_sync.sock;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 28800;  # Set the timeout to 8 hours
}
}

Enable the new configuration and restart Nginx:
sudo ln -s /etc/nginx/sites-available/myapp /etc/nginx/sites-enabled/
sudo systemctl restart nginx

Running the Application

Start the Gunicorn service:
sudo systemctl start nano_sync.service
Enable the service to start on boot:
sudo systemctl enable nano_sync.service
Debugging

Check Gunicorn logs:
sudo tail -f /var/www/nano_sync/error.log

Check Nginx logs for errors:
sudo tail -f /var/log/nginx/error.log

Troubleshoot common issues like 502 Bad Gateway:

Ensure Gunicorn is running and accessible.
Verify Nginx configuration for correct proxy settings.
Additional Resources

Flask Documentation: https://flask.palletsprojects.com/
Gunicorn Documentation: https://docs.gunicorn.org/
Nginx Documentation: https://nginx.org/en/docs/
Feel free to modify or add any other necessary sections or information based on your application's specific requirements!


