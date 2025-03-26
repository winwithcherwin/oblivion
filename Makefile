OBLIVION = python -m oblivion
BOOTSTRAP_DIR := .bootstrap
BOOTSTRAP_PACKER := $(BOOTSTRAP_DIR)/packer
BOOTSTRAP_TERRAFORM := $(BOOTSTRAP_DIR)/terraform
BOOTSTRAP_WIREGUARD := $(BOOTSTRAP_DIR)/wireguard
BOOTSTRAP_INFRA_VALID := $(BOOTSTRAP_DIR)/infra-ok

ANSIBLE_SYSTEM_DIR := oblivion/engine/ansible/playbooks/system

PACKER_FILE := packer/packer.pkr.hcl

.DEFAULT_GOAL := help

.PHONY: help world update destroy status
.PHONY: terraform-init terraform-plan terraform-apply terraform-destroy terraform-fmt
.PHONY: packer bootstrap-packer
.PHONY: wireguard-init wireguard-refresh wireguard-teardown wireguard-status
.PHONY: bootstrap-packer bootstrap-wireguard force-bootstrap wipe-bootstrap
.PHONY: run-playbooks test-playbooks
.PHONY: ssh provision-dotenv validate-redis-uri tree validate-infra fmt


# CORE
help:
	@echo "available targets:"
	@grep -E '^[a-zA-Z0-9_.-]+:.*?##' $(MAKEFILE_LIST) | \
	awk -F ':|##' '{ printf "\033[36m%-20s\033[0m %s\n", $$1, $$3 }'

genesis: bootstrap-packer terraform-apply

world: genesis validate-infra bootstrap-wireguard run-playbooks ## builds everything

update: terraform-apply validate-infra ## run terraform apply and playbooks
	@echo "waiting after terraform apply..."
	#@$(MAKE) --no-print-directory run-playbooks

timestamp-motd:
	{ \
	  echo "#!/usr/bin/env python3"; \
	  echo "# updated at: $$(date -u)"; \
	  cat $(ANSIBLE_SYSTEM_DIR)/files/motd/_template; \
	} > $(ANSIBLE_SYSTEM_DIR)/files/motd/01-oblivion
	@chmod +x $(ANSIBLE_SYSTEM_DIR)/files/motd/01-oblivion

git-update-fix: timestamp-motd
	@git add -A
	@git commit -m "Test fix"
	@git push
	@$(MAKE) update
	@$(MAKE) ssh

destroy: terraform-destroy wipe-bootstrap ## destroy infra
	@sed -i '/^REDIS_URI=/d' .env

nuke: destroy nuke-bootstrap ## destroy *everything* (forces packer to rebuild, on next run)

status: ## show bootstrap status timestamps (sorted, relative)
	@utils/bootstrap_status.sh $(BOOTSTRAP_DIR)


## PACKER
packer: ## build images with packer
	packer init $(PACKER_FILE)
	packer build $(PACKER_FILE)

bootstrap-packer:
	@if [ ! -f $(BOOTSTRAP_PACKER) ]; then \
		$(MAKE) --no-print-directory packer; \
		mkdir -p $(BOOTSTRAP_DIR); \
		date >  $(BOOTSTRAP_PACKER); \
	fi


## TERRAFORM
terraform-init: ## initialize terraform
	terraform -chdir=terraform init
	
terraform-check-vars:
	@if [ -z "$(MY_SSH_KEY_NAME)" ] || [ -z "$(MY_SOURCE_IP)" ]; then \
		echo "Set MY_SSH_KEY_NAME and MY_SOURCE_IP before running Terraform"; exit 1; \
	fi

terraform-plan: terraform-check-vars terraform-init ## terraform plan
	terraform -chdir=terraform plan -var="ssh_key_name=$(MY_SSH_KEY_NAME)" -var="my_source_ip=$(MY_SOURCE_IP)/32"

terraform-apply: terraform-check-vars terraform-init ## terraform apply
	terraform -chdir=terraform apply -auto-approve -var="ssh_key_name=$(MY_SSH_KEY_NAME)" -var="my_source_ip=$(MY_SOURCE_IP)/32"
	@date > $(BOOTSTRAP_TERRAFORM)

when-terraform-bootstrapped:
	@if [ ! -f $(BOOTSTRAP_TERRAFORM) ]; then \
		echo "Terraform did not bootstrap. Run \'make terraform-apply\' first."; \
		exit 1; \
	fi

terraform-destroy: ## terraform destroy
	terraform -chdir=terraform destroy -var="ssh_key_name=$(MY_SSH_KEY_NAME)" -var="my_source_ip=$(MY_SOURCE_IP)/32"


## VALIDATE
validate-infra: when-terraform-bootstrapped provision-dotenv validate-redis-uri test-playbooks
	@date > $(BOOTSTRAP_INFRA_VALID)

validate-redis-uri:
	@echo "making sure we can connect to redis"
	$(OBLIVION) terraform validate redis-uri

provision-dotenv: ## set your .env
	@echo "provisioning dotenv"
	python utils/tfvar2dotenv.py redis_uri || { echo "failed to extract redis_uri"; exit 1; }
	@direnv allow

when-infra-valid:
	@if [ ! -f $(BOOTSTRAP_INFRA_VALID) ]; then \
		echo "infra not valid yet, refusing to run"; \
		exit 1; \
	fi


## PLAYBOOKS
test-playbooks: when-terraform-bootstrapped ## test simple playbook
	# this will revoke INFRA_VALID if ansible fails
	if ! $(OBLIVION) ansible run --all echo; then \
		echo "Ansible run failed"; \
		rm -f $(BOOTSTRAP_INFRA_VALID); \
		exit 1; \
	fi

run-playbooks: when-infra-valid
	$(OBLIVION) ansible run --all system/motd
	$(OBLIVION) ansible run --all system/zsh
	@date > $(BOOTSTRAP_INFRA_VALID)


# WIREGUARD
wireguard-init: when-infra-valid ## setup WireGuard
	$(OBLIVION) wireguard register --all
	$(OBLIVION) wireguard write-config --all

bootstrap-wireguard: wireguard-init
	@if [ ! -f $(BOOTSTRAP_WIREGUARD) ]; then \
		echo "waiting for wireguard to settle..."; \
		sleep 3; \
	fi
	$(OBLIVION) ansible run --all wireguard
	$(OBLIVION) wireguard ping
	$(OBLIVION) ansible run --all wireguard/update-hosts
	@mkdir -p $(BOOTSTRAP_DIR)
	@date > $(BOOTSTRAP_WIREGUARD)

wireguard-refresh: when-infra-valid ## removes stale nodes and regenerate WireGuard connections everywhere
	$(OBLIVION) wireguard ping
	$(OBLIVION) wireguard write-config --all

## Teardown WireGuard from a node (removes keys, config, service)
wireguard-teardown: when-infra-valid ## make teardown-one QUEUE=server3
	$(OBLIVION) ansible run wireguard/teardown --queue $(QUEUE)

wireguard-status: when-infra-valid ## ping all nodes; remove unreachable ones from Redis
	$(OBLIVION) wireguard status --all


# MISC
ssh: ## use fzf to ssh into host
	bash ./utils/ssh.sh

tree:
	tree -aI .git -I .terraform

force-bootstrap:
	@mkdir -p $(BOOTSTRAP_DIR)
	@date > $(BOOTSTRAP_PACKER)
	@date > $(BOOTSTRAP_TERRAFORM)
	@date > $(BOOTSTRAP_WIREGUARD)
	@date > $(BOOTSTRAP_INFRA_VALID)

wipe-bootstrap:
	@rm -rf $(BOOTSTRAP_TERRAFORM)
	@rm -rf $(BOOTSTRAP_WIREGUARD)
	@rm -rf $(BOOTSTRAP_INFRA_VALID)

nuke-bootstrap:
	@rm -rf $(BOOTSTRAP_DIR)

fmt: ## format all hcl
	terraform -chdir=terraform fmt
	packer fmt packer
