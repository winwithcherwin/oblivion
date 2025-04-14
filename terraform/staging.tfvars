redis_cluster_name   = "redis-staging-0"
ssh_public_key_path  = "~/.ssh/id_ed25519.pub"
ssh_private_key_path = "~/.ssh/id_ed25519"

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

