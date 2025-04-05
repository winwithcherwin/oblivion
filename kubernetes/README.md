# Kubernetes


## Bootstrap flux
https://fluxcd.io/flux/installation/bootstrap/github/
```
flux bootstrap github \
  --owner=winwithcherwin \
  --repository=oblivion \
  --branch=main \
  --path=kubernetes/clusters/development
```

## Troubleshooting
```
kubectl describe clustersecretstore openbao -n external-secrets
```

Enable k8s output debugging
```
# /etc/rancher/k3s/config.yaml
bind-address: 10.8.0.4
flannel-iface: wg0
disable:
  - traefik
write-kubeconfig-mode: "0644"
tls-san:
  - 10.8.0.4
kube-apiserver-arg:
  - audit-log-path=-
  - audit-policy-file=/var/lib/rancher/k3s/server/audit-policy.yaml

# sudo tee /var/lib/rancher/k3s/server/audit-policy.yaml > /dev/null <<EOF
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
  - level: Metadata
    resources:
      - group: "authentication.k8s.io"
        resources: ["tokenreviews"]
EOF
```
