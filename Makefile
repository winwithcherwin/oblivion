OBLIVION = python -m oblivion
BOOTSTRAP_DIR := .bootstrap
BOOTSTRAP_PACKER := $(BOOTSTRAP_DIR)/packer
BOOTSTRAP_TERRAFORM := $(BOOTSTRAP_DIR)/terraform
BOOTSTRAP_WIREGUARD := $(BOOTSTRAP_DIR)/wireguard
BOOTSTRAP_INFRA_VALID := $(BOOTSTRAP_DIR)/infra-ok

PACKER_FILE := packer/packer.pkr.hcl

.DEFAULT_GOAL := help

.PHONY: help world update destroy status
.PHONY: terraform-init terraform-plan terraform-apply terraform-destroy terraform-fmt
.PHONY: packer bootstrap-packer
.PHONY: wireguard-init wireguard-refresh wireguard-teardown wireguard-status
.PHONY: bootstrap-packer bootstrap-terraform bootstrap-wireguard force-bootstrap reset-bootstrap
.PHONY: run-playbooks test-playbooks
.PHONY: ssh dotenv dotenv-redis-uri tree infra-check fmt


# CORE
help:
	@echo "available targets:"
	@grep -E '^[a-zA-Z0-9_.-]+:.*?##' $(MAKEFILE_LIST) | \
	awk -F ':|##' '{ printf "\033[36m%-20s\033[0m %s\n", $$1, $$3 }'

world: bootstrap-packer bootstrap-terraform infra-check bootstrap-wireguard run-playbooks ## build *everything*

update: terraform-apply ## run terraform apply and playbooks
	@echo "waiting after terraform apply..."
	@sleep 1
	@$(MAKE) --no-print-directory run-playbooks

git-update-fix:
	@git add -A
	@git commit -m "Fix"
	@git push
	@$(MAKE) update

destroy: terraform-destroy reset-bootstrap ## destroy *everything*

status: ## show bootstrap status timestamps (sorted, relative)
	@utils/bootstrap_status.sh $(BOOTSTRAP_DIR)


## PACKER
packer: ## build images with packer
	packer init $(PACKER_FILE); \
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
	
terraform-plan: terraform-init ## terraform plan
	terraform -chdir=terraform plan -var="ssh_key_name=$(MY_SSH_KEY_NAME)" -var="my_source_ip=$(MY_SOURCE_IP)/32"

terraform-apply: terraform-init ## terraform apply
	terraform -chdir=terraform apply -auto-approve -var="ssh_key_name=$(MY_SSH_KEY_NAME)" -var="my_source_ip=$(MY_SOURCE_IP)/32"
	@if [ -f $(BOOTSTRAP_TERRAFORM) ]; then \
		$(MAKE) --no-print-directory dotenv; \
		date > $(BOOTSTRAP_TERRAFORM); \
	fi


bootstrap-terraform: terraform-apply
	@if [ ! -f $(BOOTSTRAP_TERRAFORM) ]; then \
		echo "waiting for hosts to settle..."; \
		mkdir -p $(BOOTSTRAP_DIR); \
		sleep 10; \
	fi
	$(MAKE) --no-print-directory dotenv
	@date > $(BOOTSTRAP_TERRAFORM)

when-terraform-bootstrapped:
	@if [ ! -f $(BOOTSTRAP_TERRAFORM) ]; then \
		echo "Terraform did not bootstrap. Run \'make world\' first."; \
		exit 1; \
	fi

terraform-destroy: ## terraform destroy
	terraform -chdir=terraform destroy -var="ssh_key_name=$(MY_SSH_KEY_NAME)" -var="my_source_ip=$(MY_SOURCE_IP)/32"


# PLAYBOOKS
test-playbooks: when-terraform-bootstrapped
	@$(OBLIVION) ansible run --all echo && \
	mkdir -p $(BOOTSTRAP_DIR); \
	date > $(BOOTSTRAP_INFRA_VALID) || \
	( rm --force $(BOOTSTRAP_INFRA_VALID) && echo "Infra validation failed" && exit 1)

infra-check: test-playbooks

when-infra-valid:
	@if [ ! -f $(BOOTSTRAP_INFRA_VALID) ]; then \
		echo "infra not valid yet, refusing to run"; \
		exit 1; \
	fi

run-playbooks: when-infra-valid
	@$(OBLIVION) ansible run --all system/motd
	@$(OBLIVION) ansible run --all system/zsh
	@date > $(BOOTSTRAP_INFRA_VALID)


# WIREGUARD
wireguard-init: when-infra-valid ## setup WireGuard
	@$(OBLIVION) wireguard --all register
	@$(OBLIVION) wireguard --all write-config

wireguard-refresh: when-infra-valid ## removes stale nodes and regenerate WireGuard connections everywhere
	@$(OBLIVION) wireguard check-liveness
	@$(OBLIVION) wireguard --all write-config

## Teardown WireGuard from a node (removes keys, config, service)
wireguard-teardown: when-infra-valid ## make teardown-one QUEUE=server3
	@$(OBLIVION) ansible run wireguard/teardown --queue $(QUEUE)

wireguard-status: when-infra-valid ## ping all nodes; remove unreachable ones from Redis
	@$(OBLIVION) wireguard --all status

bootstrap-wireguard: wireguard-init
	@if [ ! -f $(BOOTSTRAP_WIREGUARD) ]; then \
		echo "waiting for wireguard to settle..."; \
		sleep 3; \
	fi
	@$(OBLIVION) ansible run --all wireguard
	@$(OBLIVION) wireguard ping
	@$(OBLIVION) ansible run --all wireguard/update-hosts
	@mkdir -p $(BOOTSTRAP_DIR)
	@date > $(BOOTSTRAP_WIREGUARD)


# MISC
ssh: ## use fzf to ssh into host
	bash ./utils/ssh.sh

dotenv-redis-uri:
	@python utils/tfvar2dotenv.py redis_uri; \
	if [ $$? -eq 0 ]; then \
	    direnv allow; \
	fi

dotenv: when-infra-valid ## set your .env (only run this after tf-apply)
	@$(MAKE) --no-print-directory dotenv-redis-uri

tree:
	tree -aI .git -I .terraform

force-bootstrap:
	@mkdir -p $(BOOTSTRAP_DIR)
	@date > $(BOOTSTRAP_PACKER)
	@date > $(BOOTSTRAP_TERRAFORM)
	@date > $(BOOTSTRAP_WIREGUARD)
	@date > $(BOOTSTRAP_INFRA_VALID)

reset-bootstrap:
	rm -rf $(BOOTSTRAP_DIR)

fmt: ## format all hcl
	terraform -chdir=terraform fmt
	packer fmt packer
