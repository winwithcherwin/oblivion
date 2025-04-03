[Peer]
PublicKey  = {{ PUBLIC_KEY }}
AllowedIPs = {{ ALLOWED_IP }}/32
{% if ENDPOINT %}
Endpoint   = {{ ENDPOINT }}:51820
{% endif %}
PersistentKeepalive = 25
