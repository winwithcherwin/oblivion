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

# Makefile for managing WireGuard mesh overlay via Celery + Redis

PYTHON=python -m oblivion wireguard

.PHONY: register write-config check-liveness full-refresh register-one write-one teardown-one

## 🔐 Register all nodes (generate keys + IP + store in Redis)
register:
	@$(PYTHON) register --all

## 🧩 Write wg0.conf on all nodes based on current peer state
write-config:
	@$(PYTHON) write-config --all

## 📡 Ping all nodes; remove unreachable ones from Redis
check-liveness:
	@$(PYTHON) check-liveness

## ♻️ Reregister and reconfigure a single node
## Usage: make register-one QUEUE=server2
register-one:
	@$(PYTHON) register --queue $(QUEUE)

## 💾 Rewrites config on a single node
## Usage: make write-one QUEUE=server2
write-one:
	@$(PYTHON) write-config --queues $(QUEUE)

## 🔁 Full refresh cycle (clean up dead peers + rewrite all configs)
full-refresh: check-liveness write-config

## 🧼 Teardown WireGuard from a node (removes keys, config, service)
## Usage: make teardown-one QUEUE=server3
teardown-one:
	@python -m oblivion ansible run wireguard/teardown --queue $(QUEUE)

