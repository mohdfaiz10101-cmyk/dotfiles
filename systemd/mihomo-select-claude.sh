#!/run/current-system/sw/bin/bash
sleep 5
curl -s -X PUT http://127.0.0.1:9091/proxies/GLOBAL \
  -H "Content-Type: application/json" \
  -d '{"name": "美国-US-3-流量倍率"}'
