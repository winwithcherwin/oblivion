resource "digitalocean_droplet" "this" {
  for_each = toset([
    for i in range(var.server_count) : "do-${i}"
  ])

  name     = each.key
  image    = data.digitalocean_images.this.images[0].id
  region   = "ams3"
  size     = "s-1vcpu-1gb"
  ssh_keys = [digitalocean_ssh_key.this.id]

  user_data = <<-EOT
#cloud-config
write_files:
  - path: /etc/oblivion.env
    permissions: "0600"
    owner: root
    content: |
      REDIS_URI="${var.redis_uri}"

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
  public_key = file("~/.ssh/id_rsa.pub")
}

