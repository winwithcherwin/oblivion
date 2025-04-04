[Peer]
PublicKey  = {{ PUBLIC_KEY }}
AllowedIPs = {{ ALLOWED_IP }}/32
PersistentKeepalive = 25
{% if ENDPOINT %}Endpoint   = {{ ENDPOINT }}:51820{% endif %}

