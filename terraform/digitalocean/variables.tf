variable "servers" {
  description = "Per-server configuration for DigitalOcean"
  type = map(object({
    region = string
    size   = string
  }))
}

variable "ssh_key_name" {
  type        = string
  description = "Name of the SSH public key"
}

variable "ssh_public_key_path" {
  type = string
  description = "Path of the SSH public key"
}
