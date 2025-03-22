variable "clouds" {
  description = "Which cloud providers to deploy to"
  type        = list(string)
  default     = ["digitalocean"]
}

variable "server_counts" {
  description = "How many servers per cloud"
  type        = map(number)
  default = {
    digitalocean = 1
  }
}

variable "ssh_key_name" {
  type    = string
  default = "cherwin@gmail.com"
}

variable "my_source_ip" {
  type = string
}

variable "git_clone_dir" {
  type = string
}

variable "git_repo_url" {
  type = string
}

