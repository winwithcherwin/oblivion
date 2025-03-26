clouds = ["digitalocean", "hetzner"]

servers = {
  digitalocean = {
    do-1 = {
      region = "ams3"
      size   = "s-1vcpu-1gb"
    }
  }
  hetzner = {
    hetzner-2 = {
      location    = "fsn1"
      server_type = "cpx11"
    }
  }
}

