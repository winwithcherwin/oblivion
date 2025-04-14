redis_cluster_name = "redis-staging-0"

clouds = ["digitalocean", "hetzner"]

servers = {
  digitalocean = {
    do-3 = {
      region = "ams3"
      size   = "s-2vcpu-2gb"
    }
  }
  hetzner = {
    hetzner-4 = {
      location    = "fsn1"
      server_type = "cx32"
    }
  }
}

