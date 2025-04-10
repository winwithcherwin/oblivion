clouds = ["digitalocean", "hetzner"]

servers = {
  digitalocean = {
    do-1 = {
      region = "ams3"
      size   = "s-2vcpu-2gb"
    }
    /*
    do-2 = {
      region = "ams3"
      size   = "s-2vcpu-2gb"
    }
    */
  }
  hetzner = {
    hetzner-2 = {
      location    = "fsn1"
      server_type = "cpx11"
    }
    /*
    hetzner-3 = {
      location    = "fsn1"
      server_type = "cpx11"
    }
    */
  }
}

