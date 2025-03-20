variable "my_source_ip" {}
variable "ssh_key_name" {}
variable "git_repo_url" {}
variable "git_clone_dir" {}

variable "server_names" {
  type = list(string)
  default = [
    "server-0",
  ]
}
