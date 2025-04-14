resource "digitalocean_droplet" "this" {
  for_each = var.servers

  name     = each.key
  region   = each.value.region
  size     = each.value.size
  image    = data.digitalocean_images.this.images[0].id
  ssh_keys = [digitalocean_ssh_key.this.id]

  user_data = <<-EOT
#cloud-config
write_files:
  - path: /etc/systemd/journald.conf
    owner: root:root
    permissions: "0644"
    content: |
      [Journal]
      Storage=persistent
      SystemMaxUse=500M
      SystemKeepFree=100M
EOT
}

resource "digitalocean_ssh_key" "this" {
  name       = var.ssh_key_name
  public_key = file(var.ssh_public_key_path)
}

data "digitalocean_images" "this" {
  sort {
    key       = "created"
    direction = "desc"
  }
  filter {
    key      = "name"
    values   = ["ubuntu-24-04-updated"]
    match_by = "substring"
  }
}

