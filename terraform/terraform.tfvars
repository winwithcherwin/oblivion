clouds = ["digitalocean", "hetzner"]

servers = {
  digitalocean = {
    do-worker-2 = {
      region = "ams3"
      size   = "s-1vcpu-1gb"
    }
    do-worker-1 = {
      region = "ams3"
      size   = "s-1vcpu-1gb"
    }
  }

  hetzner = {
    hz-worker-1 = {
      location    = "fsn1"
      server_type = "cpx11"
    }
  }
}

