#!/bin/bash

REPO_URL="$1"
REPO_DIR="$2"
CELERY_SERVICE="oblivion"

while ! grep "Cloud-init .* finished" /var/log/cloud-init.log; do
    echo "$(date -Ins) Waiting for cloud-init to finish"
    sleep 2
done

if [ -d "$REPO_DIR/.git" ]; then
  echo "Repository already exists in $REPO_DIR. Pulling latest changes..."
  cd "$REPO_DIR" && git fetch origin && git reset --hard origin/main

else
  echo "Cloning repository $REPO_URL into $REPO_DIR..."
  git clone --depth 1 --branch main "$REPO_URL" /opt/oblivion
fi

echo "Restarting OBLIVION"
sudo systemctl restart $CELERY_SERVICE
