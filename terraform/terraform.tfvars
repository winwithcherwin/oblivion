clouds = ["digitalocean", "hetzner"]

servers = {
  digitalocean = {
    do-worker-0 = {
      region = "ams3"
      size   = "s-1vcpu-1gb"
    }
  }

  /*
  hetzner = {
    hz-api-0 = {
      location    = "fsn1"
      server_type = "cx11"
    }
    hz-worker-1 = {
      location    = "nbg1"
      server_type = "cx21"
    }
  }
  */
}

