output "all_hosts" {
  value = local.all_hosts
}

output "redis_uri" {
  value     = module.redis.uri
  sensitive = true
}
