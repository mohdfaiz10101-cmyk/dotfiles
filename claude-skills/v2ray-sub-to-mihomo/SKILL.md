---
name: v2ray-sub-to-mihomo
description: "将良心云等服务商的 base64 编码 V2Ray 订阅（vless://、hysteria2://）转换为 Mihomo/Clash YAML 配置并热部署到 /etc/mihomo/config.yaml"
user-invocable: false
version: "1.0.0"
category: proxy
tags: [mihomo, v2ray, vless, hysteria2, clash, subscription]
effort: medium
auto-generated: true
created: 2026-04-21
---

# V2Ray Sub To Mihomo

## 场景
1. curl --noproxy '*' 下载订阅到 /tmp/raw.b64\n2. base64 解码得到多行 URI\n3. 解析 vless://（uuid@host:port?security=reality&pbk=&sid=&sni=）和 hysteria2://（password@host:port/?insecure=1&sni=）\n4. 过滤 server==127.0.0.1 的信息节点\n5. 去重名称，生成完整 Mihomo YAML（mixed-port/dns/proxies/proxy-groups/rules）\n6. sudo cp → /etc/mihomo/config.yaml && chmod 644\n7. sudo systemctl restart mihomo && curl 127.0.0.1:9091/configs 验证\n注意：port 字段需 .rstrip('/') 处理；fake-ip-filter 中 *.lan 需加引号

## 步骤
See content summary.

## 注意事项
Auto-generated from brief summary.
