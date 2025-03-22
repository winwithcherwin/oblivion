resource "digitalocean_database_cluster" "this" {
  name       = "redis-cluster-0"
  engine     = "redis"
  version    = "7"
  size       = var.size
  region     = var.region
  node_count = 1
}

resource "digitalocean_database_firewall" "this" {
  cluster_id = digitalocean_database_cluster.this.id

  rule {
    type  = "ip_addr"
    value = var.my_source_ip
  }

  dynamic "rule" {
    for_each = var.external_ips
    content {
      type  = "ip_addr"
      value = rule.value
    }
  }
}

