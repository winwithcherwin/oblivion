variable "region" {
  type    = string
  default = "ams3"
}

variable "size" {
  type    = string
  default = "db-s-1vcpu-1gb"
}

variable "my_source_ip" {
  type = string
}

variable "external_ips" {
  type = list(string)
  description = "IP addresses allowed to access Redis"
}
