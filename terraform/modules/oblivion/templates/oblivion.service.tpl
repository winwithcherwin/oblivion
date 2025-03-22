[Unit]
Description=Oblivion Worker
After=network.target
ConditionPathExists=/opt/oblivion/oblivion/celery_app.py

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/oblivion
EnvironmentFile=/etc/oblivion.env
Environment="C_FORCE_ROOT=1"
Environment="PATH=/opt/oblivion-venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
ExecStart=/opt/oblivion-venv/bin/celery -A oblivion.celery_app worker --loglevel=debug --queues=${queue_name}
Restart=always

[Install]
WantedBy=multi-user.target
