.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo "available targets:"
	@grep -E '^[a-zA-Z0-9_.-]+:.*?##' $(MAKEFILE_LIST) | \
	awk -F ':|##' '{ printf "\033[36m%-20s\033[0m %s\n", $$1, $$3 }'

tfinit: ## initialize terraform
	terraform -chdir=terraform init
	
tfplan: tfinit ## terraform plan
	terraform -chdir=terraform plan -var="ssh_key_name=$(MY_SSH_KEY_NAME)" -var="my_source_ip=$(MY_SOURCE_IP)/32"

tfapply: ## terraform apply
	echo yes | terraform -chdir=terraform apply -var="ssh_key_name=$(MY_SSH_KEY_NAME)" -var="my_source_ip=$(MY_SOURCE_IP)/32"
	$(MAKE) dotenv

tfdestroy: ## terraform destroy
	terraform -chdir=terraform destroy -var="ssh_key_name=$(MY_SSH_KEY_NAME)" -var="my_source_ip=$(MY_SOURCE_IP)/32"

fmt: ## format all hcl
	terraform -chdir=terraform fmt
	packer fmt packer

ssh: ## use fzf to ssh into host
	bash ./utils/ssh.sh

.PHONY: packer
packer: ## build images with packer
	packer init packer/packer.pkr.hcl ;\
	packer build packer/packer.pkr.hcl

dotenv-redis-uri:
	@python utils/tfvar2dotenv.py redis_uri; \
	if [ $$? -eq 0 ]; then \
	    direnv allow; \
	fi

dotenv: dotenv-redis-uri ## set your .env (only run this after tf-apply)

tree:
	tree -aI .git -I .terraform

OBLIVION=python -m oblivion

wg-livetest: ## run test task
	@$(OBLIVION) calc add 5 7 --all
	@$(OBLIVION) ansible run echo/cherwin --all
	@$(OBLIVION) ansible run echo --all

wg: ## setup WireGuard
	@$(OBLIVION) wireguard register --all
	@$(OBLIVION) wireguard write-config --all
	@$(OBLIVION) ansible run wireguard --all
	@$(OBLIVION) wireguard status --all

wg-refresh: ## removes stale nodes and regenerate WireGuard connections everywhere
	@$(OBLIVION) wireguard check-liveness
	@$(OBLIVION) wireguard write-config --all
	@$(OBLIVION) ansible run wireguard --all

## 🧼 Teardown WireGuard from a node (removes keys, config, service)
wg-teardown: ## make teardown-one QUEUE=server3
	@$(OBLIVION) ansible run wireguard/teardown --queue $(QUEUE)


wg-alive:  ## ping all nodes; remove unreachable ones from Redis
	@$(OBLIVION) wireguard check-liveness

