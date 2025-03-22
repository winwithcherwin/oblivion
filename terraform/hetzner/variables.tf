variable "servers" {
  description = "Per-server configuration for Hetzner"
  type = map(object({
    server_type = string
    location    = string
  }))
}

variable "ssh_key_name" {
  type        = string
  description = "Name of the SSH key"
}
