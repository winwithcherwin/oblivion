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

tfmt: ## terraform fmt
	terraform -chdir=terraform fmt

ssh: ## use fzf to ssh into host
	bash ./utils/ssh.sh

.PHONY: packer
packer: ## run packer
	packer plugins install github.com/hashicorp/digitalocean
	cd packer ; packer build digitalocean.json

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
