#!/usr/bin/env bash

set -e

# Fetch server IPs as JSON
json=$(terraform -chdir=terraform output -json)

# Parse the object (server name → IP) using jq
mapfile -t choices < <(echo "$json" | jq -r '.server_ips.value | to_entries[] | "\(.key)\t\(.value)"')

if [ ${#choices[@]} -eq 0 ]; then
  echo "❌ No servers found in Terraform output"
  exit 1
fi

# Use fzf to select one
selected=$(printf '%s\n' "${choices[@]}" | fzf --ansi --prompt="Select server: ")

if [ -z "$selected" ]; then
  echo "❌ No selection made."
  exit 1
fi

# Split selected line: "server-0 <tab> 1.2.3.4"
server_name=$(echo "$selected" | cut -f1)
ip=$(echo "$selected" | cut -f2)

echo "🔗 Connecting to $server_name at $ip"
exec ssh "root@$ip"

