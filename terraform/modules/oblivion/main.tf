resource "null_resource" "provision" {
  for_each = var.hosts

  triggers = {
    always_run = timestamp()
  }

  connection {
    type        = "ssh"
    host        = each.value
    user        = "root"
    private_key = file("~/.ssh/id_rsa")
  }

  provisioner "file" {
    content     = templatefile("${path.module}/templates/oblivion.service.tpl", { queue_name = each.key })
    destination = "/etc/systemd/system/oblivion.service"
  }

  provisioner "file" {
    source      = "${path.module}/scripts/git_clone.sh"
    destination = "/root/git_clone.sh"
  }

  provisioner "remote-exec" {
    inline = [
      "chmod +x /root/git_clone.sh",
      "/root/git_clone.sh ${var.git_repo_url} ${var.git_clone_dir}"
    ]
  }

  provisioner "remote-exec" {
    inline = [
      "systemctl daemon-reload",
      "systemctl enable oblivion.service",
      "systemctl restart oblivion.service"
    ]
  }
}

