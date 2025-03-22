locals {
  digitalocean_hosts = contains(var.clouds, "digitalocean") ? module.digitalocean[0].hosts : {}
  all_hosts          = merge(local.digitalocean_hosts)
}

module "digitalocean" {
  source       = "./digitalocean"
  count        = contains(var.clouds, "digitalocean") ? 1 : 0
  my_source_ip = var.my_source_ip
  ssh_key_name = var.ssh_key_name
  server_count = lookup(var.server_counts, "digitalocean", 0)
  redis_uri    = module.redis.uri
}

module "oblivion" {
  source = "./modules/oblivion"

  hosts = local.all_hosts

  git_repo_url  = var.git_repo_url
  git_clone_dir = var.git_clone_dir
}

module "redis" {
  source       = "./modules/redis"
  my_source_ip = var.my_source_ip
  external_ips = values(local.all_hosts)
}
