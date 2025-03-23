packer {
  required_plugins {
    digitalocean = {
      version = ">= 1.0.0"
      source  = "github.com/hashicorp/digitalocean"
    }
    hcloud = {
      version = ">= 1.0.0"
      source  = "github.com/hetznercloud/hcloud"
    }
    ansible = {
      version = ">= 1.0.0"
      source  = "github.com/hashicorp/ansible"
    }
  }
}

locals {
  do_base_image   = "ubuntu-24-04-x64"
  hz_base_image   = "ubuntu-24.04"
  snapshot_suffix = format("ubuntu-24-04-updated-%s", timestamp())
}

source "digitalocean" "ubuntu" {
  image         = local.do_base_image
  region        = "ams3"
  size          = "s-1vcpu-1gb"
  ssh_username  = "root"
  snapshot_name = local.snapshot_suffix
}

source "hcloud" "ubuntu" {
  image         = local.hz_base_image
  location      = "fsn1"
  server_type   = "cpx11"
  ssh_username  = "root"
  snapshot_name = local.snapshot_suffix
  snapshot_labels = {
    name = "oblivion"
  }
}

build {
  name = "server"
  sources = [
    "source.digitalocean.ubuntu",
    "source.hcloud.ubuntu"
  ]

  provisioner "file" {
    source      = "oblivion/requirements.txt"
    destination = "/tmp/requirements.txt"
  }

  provisioner "shell" {
    script       = "packer/scripts/wait-for-cloud-init.sh"
    pause_before = "10s"
  }

  provisioner "ansible" {
    playbook_file   = "packer/ansible/base.yaml"
    user            = "root"
    extra_arguments = ["--scp-extra-args", "'-O'"]
  }
}

