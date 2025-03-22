resource "hcloud_server" "this" {
  for_each = var.servers

  name        = each.key
  server_type = each.value.server_type
  location    = each.value.location
  image       = data.hcloud_image.this.id
  ssh_keys    = [hcloud_ssh_key.this.id]
}

resource "hcloud_ssh_key" "this" {
  name      = var.ssh_key_name
  public_key = file("~/.ssh/id_rsa.pub")
}

data "hcloud_image" "this" {
  with_selector = "name=oblivion"
  most_recent = true
}

