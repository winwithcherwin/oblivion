#!/usr/bin/env bash

BOOTSTRAP_DIR="${1:-.bootstrap}"

echo "Bootstrap Status:"
mkdir -p "$BOOTSTRAP_DIR"

files=$(find "$BOOTSTRAP_DIR" -type f -printf "%T@ %p\n" | sort -n)

if [ -z "$files" ]; then
  echo "No bootstrap markers found."
  exit 0
fi

while read -r line; do
  timestamp=$(echo "$line" | cut -d' ' -f1)
  file=$(echo "$line" | cut -d' ' -f2)
  label=$(basename "$file")
  time_str=$(cat "$file")
  now=$(date +%s)
  diff=$(echo "$now - $timestamp" | bc | cut -d'.' -f1)

  if [ "$diff" -lt 60 ]; then rel_time="${diff}s ago"
  elif [ "$diff" -lt 3600 ]; then rel_time="$((diff/60))m ago"
  elif [ "$diff" -lt 86400 ]; then rel_time="$((diff/3600))h ago"
  else rel_time="$((diff/86400))d ago"
  fi

  printf "\033[36m%-20s\033[0m %s (%s)\n" "$label" "$time_str" "$rel_time"
done <<< "$files"

