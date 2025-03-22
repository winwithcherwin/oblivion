variable "servers" {
  description = "Per-server configuration for DigitalOcean"
  type = map(object({
    region = string
    size   = string
  }))
}

variable "ssh_key_name" {
  type        = string
  description = "Name of the SSH key"
}
