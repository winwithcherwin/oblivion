variable "clouds" {
  description = "Which cloud providers to deploy to"
  type        = list(string)
  default     = ["digitalocean"]
}

variable "servers" {
  description = "Map of per-cloud per-server configs"
  type = map(map(object({
    region      = optional(string)
    size        = optional(string)
    location    = optional(string)
    server_type = optional(string)
  })))
}

variable "ssh_key_name" {
  type = string
}

variable "my_source_ip" {
  type      = string
  sensitive = true
}

variable "git_clone_dir" {
  type    = string
  default = "/opt/oblivion"
}

variable "git_repo_url" {
  type    = string
  default = "https://github.com/winwithcherwin/oblivion"
}

