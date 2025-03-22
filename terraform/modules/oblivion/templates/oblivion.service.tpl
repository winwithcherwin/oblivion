[Unit]
Description=Oblivion Worker
After=network.target

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/opt/oblivion
EnvironmentFile=/etc/oblivion.env
Environment="PYTHONPATH=/opt/oblivion"
Environment="C_FORCE_ROOT=1"
ExecStart=/usr/bin/python3 -m celery -A oblivion.celery_app worker --loglevel=debug --queues=${queue_name}
Restart=always

[Install]
WantedBy=multi-user.target
