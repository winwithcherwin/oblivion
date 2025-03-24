#!/usr/bin/env bash
set -e

# Fetch server IPs as JSON
json=$(terraform -chdir=terraform output -json)

# Get list of "name<TAB>ip"
mapfile -t choices < <(echo "$json" | jq -r '.all_hosts.value | to_entries[] | "\(.key)\t\(.value)"')

if [ ${#choices[@]} -eq 0 ]; then
  echo "❌ No servers found in Terraform output"
  exit 1
fi

if [ ${#choices[@]} -eq 1 ]; then
  line="${choices[0]}"
  server_name=$(echo "$line" | cut -f1)
  ip=$(echo "$line" | cut -f2)
  echo "🔗 Connecting to $server_name at $ip"
  ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "root@$ip" cat /etc/update-motd.d/01-oblivion
  exec ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "root@$ip"
fi

# Use fzf to select one
selected=$(printf '%s\n' "${choices[@]}" | fzf --ansi --prompt="Select server: ")

if [ -z "$selected" ]; then
  echo "❌ No selection made."
  exit 1
fi

server_name=$(echo "$selected" | cut -f1)
ip=$(echo "$selected" | cut -f2)

echo "🔗 Connecting to $server_name at $ip"
exec ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "root@$ip"

