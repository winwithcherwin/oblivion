output "all_hosts" {
  value = merge(
    module.digitalocean[*].hosts...
  )
}

output "redis_uri" {
  value     = module.redis.uri
  sensitive = true
}
