output "redis_uri" {
  value     = digitalocean_database_cluster.redis.uri
  sensitive = true
}

output "server_ips" {
  value = { for k, v in digitalocean_droplet.this : k => v.ipv4_address }
}
