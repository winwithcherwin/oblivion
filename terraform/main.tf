locals {

  digitalocean_hosts = contains(var.clouds, "digitalocean") ? module.digitalocean[0].hosts : {}
  hetzner_hosts      = contains(var.clouds, "hetzner") ? module.hetzner[0].hosts : {}

  all_hosts = merge(
    local.digitalocean_hosts,
    local.hetzner_hosts
  )
}

module "digitalocean" {
  source = "./digitalocean"
  count  = contains(var.clouds, "digitalocean") ? 1 : 0

  servers      = lookup(var.servers, "digitalocean", {})
  ssh_key_name = var.ssh_key_name
}

module "hetzner" {
  source = "./hetzner"
  count  = contains(var.clouds, "hetzner") ? 1 : 0

  servers      = lookup(var.servers, "hetzner", {})
  ssh_key_name = var.ssh_key_name
}

module "oblivion" {
  source = "./modules/oblivion"
  hosts  = local.all_hosts

  git_repo_url  = var.git_repo_url
  git_clone_dir = var.git_clone_dir

  redis_uri = module.redis.uri
}

module "redis" {
  source = "./modules/redis"

  my_source_ip = var.my_source_ip
  external_ips = values(local.all_hosts)
}
