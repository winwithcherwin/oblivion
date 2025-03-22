output "hosts" {
  value = {
    for k, v in digitalocean_droplet.this :
      k => v.ipv4_address
  }
}
