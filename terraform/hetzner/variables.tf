variable "server_count" {
  type        = number
  description = "Number of Hetzner servers to create"
}

variable "server_type" {
  type        = string
  default     = "cx11"
}

variable "location" {
  type        = string
  default     = "fsn1"
}

variable "ssh_key_name" {
  type        = string
  description = "Name of the SSH key"
}
