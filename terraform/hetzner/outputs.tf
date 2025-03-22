output "hosts" {
  value = {
    for s in hcloud_server.this :
      s.name => s.ipv4_address
  }
}

