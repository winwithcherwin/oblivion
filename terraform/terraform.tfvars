clouds = ["digitalocean", "hetzner"]

servers = {
  digitalocean = {
    do = {
      region = "ams3"
      size   = "s-1vcpu-1gb"
    }
  }
  hetzner = {
    he = {
      location    = "fsn1"
      server_type = "cpx11"
    }
  }
}

