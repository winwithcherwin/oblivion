clouds = ["digitalocean", "hetzner"]

servers = {
  digitalocean = {
    digitalocean-worker-10 = {
      region = "ams3"
      size   = "s-1vcpu-1gb"
    }
    digitalocean-worker-20 = {
      region = "ams3"
      size   = "s-1vcpu-1gb"
    }
  }
  hetzner = {
    hetzner-worker-30 = {
      location    = "fsn1"
      server_type = "cpx11"
    }
    hetzner-worker-40 = {
      location    = "fsn1"
      server_type = "cpx11"
    }
  }
}

