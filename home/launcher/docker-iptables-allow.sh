#!/run/current-system/sw/bin/bash
# Allow Docker bridge networks to access host Ollama (11434) and other services
# This is needed because NixOS firewall blocks Docker bridge -> host traffic
# Created: 2026-04-09

set -euo pipefail

# Ports that Docker containers need to access on host
PORTS=(11434 7890 7891)  # Ollama + Xray 代理

# Get all Docker network subnets dynamically
subnets=$(docker network ls --format '{{.Name}}' 2>/dev/null | while read -r net; do
    docker network inspect "$net" --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}' 2>/dev/null
done | sort -u)

for subnet in $subnets; do
    for port in "${PORTS[@]}"; do
        # Check if rule already exists
        if ! iptables -C nixos-fw -s "$subnet" -p tcp --dport "$port" -j ACCEPT 2>/dev/null; then
            iptables -I nixos-fw 1 -s "$subnet" -p tcp --dport "$port" -j ACCEPT
            echo "Added: $subnet -> tcp/$port"
        else
            echo "Exists: $subnet -> tcp/$port"
        fi
    done
done

echo "Docker iptables rules applied successfully"
