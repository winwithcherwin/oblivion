variable "hosts" {
  description = "Map of hostname => { ip, name }"
  type        = map(string)
}

variable "git_repo_url" {
  type = string
}

variable "git_clone_dir" {
  type = string
}

variable "redis_uri" {
  type = string
}

variable "ssh_private_key_path" {
  type        = string
  description = "Path of the SSH public key"
}
