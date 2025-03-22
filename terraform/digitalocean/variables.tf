variable "ssh_key_name" {}

variable "servers" {
  description = "Per-server configuration for DigitalOcean"
  type = map(object({
    region = string
    size   = string
  }))
}
