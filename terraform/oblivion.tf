resource "null_resource" "provision_oblivion" {
  for_each = digitalocean_droplet.this

  triggers = {
    always_run = "${timestamp()}"
  }

  provisioner "file" {
    content     = templatefile("${path.module}/templates/oblivion.service.tpl", { queue_name = each.value.name })
    destination = "/etc/systemd/system/oblivion.service"
  }

  provisioner "file" {
    source      = "./scripts/git_clone.sh"
    destination = "/root/git_clone.sh"
  }

  provisioner "remote-exec" {
    inline = [
      "chmod +x /root/git_clone.sh",
      "/root/git_clone.sh ${var.git_repo_url} ${var.git_clone_dir}",
    ]
  }

  provisioner "remote-exec" {
    inline = [
      "systemctl daemon-reload",
      "systemctl enable oblivion.service",
      "systemctl restart oblivion.service",
    ]
  }

  connection {
    type        = "ssh"
    host        = each.value.ipv4_address
    user        = "root"
    private_key = file("~/.ssh/id_rsa")
  }
}

