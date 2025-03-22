data "digitalocean_images" "this" {
  sort {
    key       = "created"
    direction = "desc"
  }
  filter {
    key      = "name"
    values   = ["ubuntu-24-04-updated"]
    match_by = "substring"
  }
}
