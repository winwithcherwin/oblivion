# ｏｂｌｉｖｉｏｎ

With great power comes great responsibility.

## Install OpenBao server


```
ob pki init
ob ansible run openbao --queue do-1 # 10.8.0.3 in my case (make sure you have VAULT_ADDR exported)
ob bao init https://10.8.0.3:8200
ob bao bootstrap-intermediate https://10.8.0.3:8200
cat .secrets/openbao.json | jq -r '.root_token' | pbcopy
# login to openbao to verify that everything is working correctly
ob bao enable-auth-approle
ob ansible run openbao/agent --queue do-1 --extra-vars-callback "oblivion.core.bao.get_vault_token" --extra-vars-callback "oblivion.core.bao.create_approle:name=pki-intermediate-issue-rfc1918-wildcard-dns,vault_addr=https://10.8.0.3:8200" -e "linux_user=openbao" -e "certificate_destination_dir=/opt/openbao/tls"
ob ansible run openbao/refresh-server --queue do-1
ob bao unseal https://10.8.0.3:8200
ob ansible run k3s --queue hetzner-2 # 10.8.0.5 in my case
# TODO:
#   * provision approle and openbao-agent
#   * give credentials to write kubeconfig to secrets path
#   * write kubeconfig to path
scp root@10.8.0.5:/etc/rancher/k3s/k3s.yaml $PWD/.secrets/k3s.yaml
export KUBECONFIG=$PWD/.secrets/k3s.yaml

kubectl create --dry-run=client -n kube-system configmap oblivion-ca-certificate --from-file=certificate=.secrets/pki/root/oblivion-ca.crt -o yaml > kubernetes/apps/oblivion/base/certificates/oblivion-ca-certificate.yaml

# git add -A .. && git push

flux bootstrap github --owner=winwithcherwin --repository=oblivion --branch=main --path=kubernetes/clusters/development # needs GITHUB PAT
kubectl kustomize kubernetes/apps/external-secrets/overlays/development | kubectl apply -f - # somehow flux get stuck so we need to help it along

flux reconcile kustomization oblivion --with-source

ob bao mount-kubernetes-backend
ob bao create-role-vault-secrets-operator --cluster-name development
```
