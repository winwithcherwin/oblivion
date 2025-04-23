
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
kubectl kustomize kubernetes/clusters/development | kubectl apply -f - # somehow flux get stuck so we need to help it along

flux reconcile kustomization oblivion --with-source

# you should now have most things running. The things that aren't running are waiting for secrets / credentials

# This integrates kubernetes backend with vault and makes sure the backend gets a new jwt periodically
ob bao mount-kubernetes-backend --vault-address https://10.8.0.3:8200 --cluster-name development
ob bao create-role-vault-secrets-operator --cluster-name development
ob bao enable-secrets-engine --cluster-name development

# Install reflector and automation controller
flux bootstrap github   --components-extra=image-reflector-controller,image-automation-controller   --owner=$GITHUB_USER   --repository=oblivion   --branch=main   --path=kubernetes/clusters/staging   --read-write-key   --personal

# Create an image update automation
flux create image update flux-system --interval=30m --git-repo-ref=flux-system --git-repo-ref=flux-system --git-repo-path="./kubernetes/clusters/staging" --checkout-branch=main --push-branch=main --author-name=fluxcdbot --author-email=fluxcdbot@noreply.winwithcherwin.com --commit-template="{{range .Changed.Changes}}{{print .OldValue}} -> {{println .NewValue}}{{end}}" --export > kubernetes/apps/oblivion/base/oblivion/ubuild-imageupdateautomation.yaml

# Start a build
kubectl annotate imagebuild oblivion trigger-build=$(date +%s) --overwrite

# now we need to copy the secrets
# TODO: save and provision secrets

# cleanup k3s node
k3s ctr images ls
k3s ctr images prune --all
```
