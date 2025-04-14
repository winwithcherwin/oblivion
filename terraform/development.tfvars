redis_cluster_name   = "redis-cluster-0"
ssh_public_key_path  = "~/.ssh/id_rsa.pub"
ssh_private_key_path = "~/.ssh/id_rsa"

clouds = ["digitalocean", "hetzner"]

servers = {
  digitalocean = {
    do-1 = {
      region = "ams3"
      size   = "s-2vcpu-2gb"
    }
  }
  hetzner = {
    hetzner-2 = {
      location    = "fsn1"
      server_type = "cx32"
    }
  }
}

