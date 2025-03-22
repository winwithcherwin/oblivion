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
  }
}

variable "cloud" {
  type    = string
  default = "digitalocean"
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
  name    = "server"
  sources = ["source.digitalocean.ubuntu"]

  provisioner "shell" {
    script       = "./scripts/wait-for-cloud-init.sh"
    pause_before = "10s"
  }

  provisioner "shell" {
    inline = [
      "export DEBIAN_FRONTEND=noninteractive",
      "apt-get update -y",
      "apt-get install -y python3 python3-venv python3-pip redis-tools ansible jina2",
      "python3 -m venv /opt/oblivion-venv",
      "/opt/oblivion-venv/bin/pip install --upgrade pip",
      "/opt/oblivion-venv/bin/pip install celery ansible-runner redis"
    ]
  }
}

build {
  name    = "server"
  sources = ["source.hcloud.ubuntu"]

  provisioner "shell" {
    script       = "./scripts/wait-for-cloud-init.sh"
    pause_before = "10s"
  }

  provisioner "shell" {
    inline = [
      "export DEBIAN_FRONTEND=noninteractive",
      "apt-get update -y",
      "apt-get install -y python3 python3-venv python3-pip redis-tools ansible",
      "python3 -m venv /opt/oblivion-venv",
      "/opt/oblivion-venv/bin/pip install --upgrade pip",
      "/opt/oblivion-venv/bin/pip install celery ansible-runner redis jinja2"
    ]

  }
}

