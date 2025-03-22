resource "hcloud_server" "this" {
  for_each = toset([
    for i in range(var.server_count) : "hz-${i}"
  ])
  name        = "each.key"
  image       = "ubuntu-22.04"
  server_type = var.server_type
  location    = var.location
  ssh_keys    = [hcloud_ssh_key.this.id]
}

resource "hcloud_ssh_key" "this" {
  name      = var.ssh_key_name
  public_key = file("~/.ssh/id_rsa.pub")
}
