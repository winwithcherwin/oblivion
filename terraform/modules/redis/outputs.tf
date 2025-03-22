output "uri" {
  value     = digitalocean_database_cluster.this.uri
  sensitive = true
}
