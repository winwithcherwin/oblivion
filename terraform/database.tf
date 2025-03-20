resource "digitalocean_database_cluster" "redis" {
  name       = "redis-cluster-0"
  engine     = "redis"
  version    = "7"
  size       = "db-s-1vcpu-1gb"
  region     = "ams3"
  node_count = 1
}

resource "digitalocean_database_firewall" "redis" {
  cluster_id = digitalocean_database_cluster.redis.id

  rule {
    type  = "ip_addr"
    value = var.my_source_ip
  }

  dynamic "rule" {
    for_each = digitalocean_droplet.this
    content {
      type  = "ip_addr"
      value = rule.value.ipv4_address
    }
  }
}
