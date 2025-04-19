* Create playbook to update /opt/oblivion-venv
* Create playbook to deploy Hashicorp Vault
    * Send .env to Vault automatically
* Create playbook to deploy openweb-ui
* Create module to deploy kubernetes (the good way)
* Install Redis on one of the VMs
    * Use dedicated redis module
    * Setup with cloud-init
    * Use own PKI
* Migrate to Python terraform
* Use Postgresql backend for terraform (migrate from files to db)
    * Have ob automatically do this after it has provisioned postgresql
        * Use docker initially
        * Then use a provisoned server
        * Bonus points, hook it up with hashicorp vault!!!
* Cleanup stale wireguard peers from /etc/wireguard.conf


* Create cronjob that continiously updates (or create) the kubernetes auth backend
* First time with wrapped response
    * Consecutive times with service-account
* Deploy reflector with flux
* Create oblivion-ca-certificate in kube-system with reflector annotations
* Install reflector
* Turnoff SKIP_VERIFY *everywhere*

* Make sure to update registries.yaml
* Make sure to update resolve.conf with k3s dns (remove symlink first and disable systemd-resolved)

* Trigger image build after webhook by modifying CR <- webhook
* After image build trigger flux image automation
