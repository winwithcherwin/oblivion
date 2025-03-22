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

packer-do: ## build digitalocean image
	cd packer; \
	packer init packer.pkr.hcl ;\
	packer build -only=server.digitalocean.ubuntu packer.pkr.hcl

packer-hz: ## build hetzner image
	cd packer; \
	packer init packer.pkr.hcl ;\
	packer build -only=server.hcloud.ubuntu packer.pkr.hcl

dotenv-redis-uri:
	@python utils/tfvar2dotenv.py redis_uri; \
	if [ $$? -eq 0 ]; then \
	    direnv allow; \
	fi

dotenv: dotenv-redis-uri ## set your .env (only run this after tf-apply)

tree:
	tree -aI .git -I .terraform

livetest: ## run test task
	python -m oblivion calc add 5 7 --all
	python -m oblivion ansible run echo/cherwin --all
	python -m oblivion ansible run echo --all
