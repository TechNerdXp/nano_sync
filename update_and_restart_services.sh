#!/bin/bash

echo "Reloading nginx..."
sudo systemctl reload nginx

echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "Restarting nano_sync service..."
sudo systemctl restart nano_sync

echo "Enabling nano_sync service to start on boot..."
sudo systemctl enable nano_sync

echo "All operations completed successfully!"
