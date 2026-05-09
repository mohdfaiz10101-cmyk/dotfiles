#!/usr/bin/env python3
"""
Merge multiple proxy subscription URLs into one Clash Meta (mihomo) config.
No external dependencies — uses only stdlib (urllib, base64, json, re).

Usage:
  python3 merge_sub.py --url <url1> --url <url2> [--output out.yaml] [--upload]

Output defaults to ~/merged_sub.yaml
"""

import argparse
import base64
import json
import os
import re
import ssl
import subprocess
import sys
import urllib.parse
import urllib.request
import yaml
import yaml


def fetch_url(url, ua=None):
    """Fetch URL content. Try without UA first, then with Clash UA."""
    for ua in [None, "ClashForAndroid/2.5.12"]:
        try:
            req = urllib.request.Request(url)
            req.add_header("User-Agent", ua if ua else "ClashForAndroid/2.5.12")
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                return resp.read()
        except Exception:
            continue


def detect_format(data):
    """Detect subscription format from raw bytes."""
    text = data.decode("utf-8", errors="ignore").strip()
    # Clash YAML
    if text.startswith("port:") or text.startswith("mixed-port:") or "proxies:" in text[:500]:
        return "clash_yaml"
    # Base64 encoded share links
    try:
        decoded = base64.b64decode(text).decode("utf-8", errors="ignore")
        if decoded.startswith("vless://") or decoded.startswith("vmess://") or decoded.startswith("trojan://") or decoded.startswith("ss://") or decoded.startswith("hysteria2://"):
            return "base64_links"
    except Exception:
        pass
    # Raw share links
    if text.startswith("vless://") or text.startswith("vmess://") or text.startswith("trojan://") or text.startswith("ss://") or text.startswith("hysteria2://"):
        return "raw_links"
    return "unknown"


def parse_clash_yaml(text):
    """Extract proxies from Clash YAML using yaml.safe_load."""
    try:
        data = yaml.safe_load(text)
        return data.get("proxies", [])
    except Exception:
        return []


def parse_vless(uri):
    """Parse vless:// URI to proxy dict."""
    uri = uri.strip()
    if not uri.startswith("vless://"):
        return None
    main, _, fragment = uri.partition("#")
    name = urllib.parse.unquote(fragment) if fragment else "vless"
    main = main[len("vless://"):]
    uuid_at, _, rest = main.partition("?")
    uuid, _, hostport = uuid_at.partition("@")
    host, _, port_str = hostport.rpartition(":")
    try:
        port = int(port_str) if port_str else 443
    except ValueError:
        port = 443
    params = urllib.parse.parse_qs(rest)

    network = params.get("type", ["tcp"])[0]
    security = params.get("security", ["none"])[0]
    flow = params.get("flow", [""])[0]
    sni = params.get("sni", [""])[0]
    fp = params.get("fp", [""])[0]
    pbk = params.get("pbk", [""])[0]
    sid = params.get("sid", [""])[0]
    path = params.get("path", [""])[0]
    host_header = params.get("host", [""])[0]

    proxy = {
        "name": name,
        "type": "vless",
        "server": host,
        "port": port,
        "uuid": uuid,
        "network": network,
        "tls": "true" if security in ("tls", "reality") else "false",
        "udp": "true",
    }

    if security == "reality":
        reality_opts = {}
        if pbk:
            reality_opts["public-key"] = pbk
        if sid:
            reality_opts["short-id"] = sid
        if reality_opts:
            proxy["reality-opts"] = json.dumps(reality_opts)
        if fp:
            proxy["client-fingerprint"] = fp
        if flow:
            proxy["flow"] = flow
    elif security == "tls":
        if sni:
            proxy["servername"] = sni
        if fp:
            proxy["client-fingerprint"] = fp

    if network == "ws":
        ws_opts = {}
        if path:
            ws_opts["path"] = urllib.parse.unquote(path)
        if host_header:
            ws_opts["headers"] = json.dumps({"Host": host_header})
        if ws_opts:
            proxy["ws-opts"] = json.dumps(ws_opts)
    elif network == "tcp" and flow:
        proxy["flow"] = flow

    if sni and security in ("tls", "reality"):
        proxy["sni"] = sni

    return proxy


def parse_hysteria2(uri):
    """Parse hysteria2:// URI to proxy dict."""
    uri = uri.strip()
    if not uri.startswith("hysteria2://"):
        return None
    main, _, fragment = uri.partition("#")
    name = urllib.parse.unquote(fragment) if fragment else "hysteria2"
    main = main[len("hysteria2://"):]
    auth_at, _, rest = main.partition("?")
    password, _, hostport = auth_at.partition("@")
    host, _, port_str = hostport.rpartition(":")
    port_str = port_str.rstrip("/")
    try:
        port = int(port_str) if port_str else 443
    except ValueError:
        port = 443
    params = urllib.parse.parse_qs(rest)

    proxy = {
        "name": name,
        "type": "hysteria2",
        "server": host,
        "port": port,
        "password": password,
        "udp": "true",
    }

    sni = params.get("sni", [""])[0]
    if sni:
        proxy["sni"] = sni

    insecure = params.get("insecure", ["0"])[0]
    if insecure == "1":
        proxy["skip-cert-verify"] = "true"

    mport = params.get("mport", [""])[0]
    if mport:
        proxy["ports"] = mport

    return proxy


def parse_trojan(uri):
    """Parse trojan:// URI to proxy dict."""
    uri = uri.strip()
    if not uri.startswith("trojan://"):
        return None
    main, _, fragment = uri.partition("#")
    name = urllib.parse.unquote(fragment) if fragment else "trojan"
    main = main[len("trojan://"):]
    password, _, rest = main.partition("@")
    hostport, _, params_str = rest.partition("?")
    host, _, port_str = hostport.rpartition(":")
    try:
        port = int(port_str) if port_str else 443
    except ValueError:
        port = 443
    params = urllib.parse.parse_qs(params_str)

    proxy = {
        "name": name,
        "type": "trojan",
        "server": host,
        "port": port,
        "password": password,
        "udp": "true",
    }

    sni = params.get("sni", [""])[0]
    if sni:
        proxy["sni"] = sni
    host_h = params.get("host", [""])[0]
    if host_h:
        proxy["sni"] = host_h
    network = params.get("type", ["tcp"])[0]
    if network == "ws":
        proxy["network"] = "ws"
        path = params.get("path", [""])[0]
        if path:
            proxy["ws-opts"] = json.dumps({"path": urllib.parse.unquote(path)})
    skip_cert = params.get("allowInsecure", ["0"])[0]
    if skip_cert == "1":
        proxy["skip-cert-verify"] = "true"

    return proxy


def parse_ss(uri):
    """Parse ss:// URI to proxy dict."""
    uri = uri.strip()
    if not uri.startswith("ss://"):
        return None
    main, _, fragment = uri.partition("#")
    name = urllib.parse.unquote(fragment) if fragment else "ss"
    main = main[len("ss://"):]
    # ss://base64(method:password)@host:port or ss://base64@host:port
    if "@" in main:
        encoded, _, hostport = main.partition("@")
        try:
            decoded = base64.b64decode(encoded + "==").decode()
            method, password = decoded.split(":", 1)
        except Exception:
            method, password = "aes-256-gcm", ""
        host, _, port_str = hostport.rpartition(":")
        try:
            port = int(port_str) if port_str else 443
        except ValueError:
            port = 443
        return {
            "name": name,
            "type": "ss",
            "server": host,
            "port": port,
            "cipher": method,
            "password": password,
            "udp": "true",
        }
    # ss://base64(method:password@host:port)
    try:
        decoded = base64.b64decode(main + "==").decode()
        userinfo, _, hostport = decoded.rpartition("@")
        method, password = userinfo.split(":", 1)
        host, _, port_str = hostport.rpartition(":")
        port = int(port_str) if port_str else 443
        return {
            "name": name,
            "type": "ss",
            "server": host,
            "port": port,
            "cipher": method,
            "password": password,
            "udp": "true",
        }
    except Exception:
        return None


def parse_share_links(text):
    """Parse share links text into proxy list."""
    proxies = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # Skip info nodes
        if "@127.0.0.1:" in line:
            continue
        decoded_name = urllib.parse.unquote(line.split("#")[-1]) if "#" in line else ""
        if "剩余" in decoded_name or "到期" in decoded_name or "流量" in decoded_name and "倍率" not in decoded_name:
            continue

        for parser in [parse_vless, parse_hysteria2, parse_trojan, parse_ss]:
            p = parser(line)
            if p:
                proxies.append(p)
                break
    return proxies


def source_proxies(url, prefix):
    """Fetch and parse a subscription URL, return proxy list with name prefix."""
    proxies = []
    data = None

    # Try plain UA first, then Clash UA
    for ua in [None, "ClashForAndroid/2.5.12"]:
        try:
            data = fetch_url(url, ua)
            text = data.decode("utf-8", errors="ignore").strip()
            # Detect blocked responses
            is_blocked = "blocked" in text.lower()
            if text.startswith("proxies:") and "name:" in text and "127.0.0.1" in text and "port: 1" in text:
                is_blocked = True
            if is_blocked:
                data = None
                continue
            break
        except Exception:
            data = None
            continue

    if data is None:
        print(f"[FAILED] Cannot fetch: {url}", file=sys.stderr)
        return []

    fmt = detect_format(data)
    text = data.decode("utf-8", errors="ignore")

    if fmt == "clash_yaml":
        proxies = parse_clash_yaml(text)
    elif fmt == "base64_links":
        decoded = base64.b64decode(text).decode("utf-8", errors="ignore")
        proxies = parse_share_links(decoded)
    elif fmt == "raw_links":
        proxies = parse_share_links(text)
    else:
        print(f"[WARN] Unknown format for: {url}", file=sys.stderr)
        try:
            decoded = base64.b64decode(text).decode("utf-8", errors="ignore")
            proxies = parse_share_links(decoded)
        except Exception:
            pass

    # Prefix names
    for p in proxies:
        p["name"] = f"{prefix}-{p.get('name', 'unknown')}"

    return proxies


def classify_region(name):
    """Classify proxy name to region tag."""
    n = name.lower()
    if any(k in n for k in ["hk", "香港", "🇭🇰"]):
        return "hk"
    if any(k in n for k in ["jp", "日本", "🇯🇵"]):
        return "jp"
    if any(k in n for k in ["us", "美国", "🇺🇸"]):
        return "us"
    if any(k in n for k in ["sg", "新加坡", "🇸🇬"]):
        return "sg"
    if any(k in n for k in ["tw", "台湾", "🇨🇳"]):
        return "tw"
    if any(k in n for k in ["kr", "韩国", "🇰🇷"]):
        return "kr"
    if any(k in n for k in ["nl", "de", "uk", "fr", "ie", "ee", "荷兰", "德国", "英国", "法国", "爱尔兰", "爱沙尼亚"]):
        return "eu"
    if any(k in n for k in ["au", "澳大利亚", "🇦🇺"]):
        return "au"
    return "other"


def build_config(all_proxies):
    """Build complete Clash Meta config from proxy list."""
    all_names = [p["name"] for p in all_proxies]

    regions = {"hk": [], "jp": [], "us": [], "sg": [], "tw": [], "kr": [], "eu": [], "au": [], "other": []}
    for p in all_proxies:
        r = classify_region(p["name"])
        regions[r].append(p["name"])

    region_groups = {
        "hk": "🇭🇰 香港",
        "jp": "🇯🇵 日本",
        "us": "🇺🇸 美国",
        "sg": "🇸🇬 新加坡",
        "tw": "🇨🇳 台湾",
        "kr": "🇰🇷 韩国",
        "eu": "🇪🇺 欧洲",
        "au": "🇦🇺 澳大利亚",
    }

    lines = [
        "mixed-port: 7890",
        "socks-port: 7891",
        "allow-lan: true",
        "mode: rule",
        "log-level: info",
        "external-controller: 127.0.0.1:9090",
        "",
        "dns:",
        "  enable: true",
        "  ipv6: false",
        "  nameserver:",
        "    - 223.5.5.5",
        "    - 119.29.29.29",
        "    - https://dns.alidns.com/dns-query",
        "  fallback:",
        "    - 8.8.8.8",
        "    - tls://1.0.0.1:853",
        "    - https://cloudflare-dns.com/dns-query",
        "  fallback-filter:",
        "    geoip: true",
        "    ipcidr:",
        "      - 240.0.0.0/4",
        "",
        "proxies:",
    ]

    for p in all_proxies:
        lines.append(f"  - name: \"{p['name']}\"")
        for k, v in p.items():
            if k == "name":
                continue
            if isinstance(v, str) and v in ("true", "false"):
                lines.append(f"    {k}: {v}")
            else:
                lines.append(f"    {k}: \"{v}\"")

    lines.append("")
    lines.append("proxy-groups:")

    select_names = ["♻️ 自动选择"] + list(region_groups.values()) + ["DIRECT"]
    lines.append("  - name: \"🚀 节点选择\"")
    lines.append("    type: select")
    lines.append("    proxies:")
    for n in select_names:
        lines.append(f"      - \"{n}\"")

    lines.append("  - name: \"♻️ 自动选择\"")
    lines.append("    type: url-test")
    lines.append("    url: http://www.gstatic.com/generate_204")
    lines.append("    interval: 300")
    lines.append("    proxies:")
    for n in all_names:
        lines.append(f"      - \"{n}\"")

    for key, label in region_groups.items():
        names = regions[key]
        if not names:
            names = ["DIRECT"]
        lines.append(f"  - name: \"{label}\"")
        lines.append("    type: url-test")
        lines.append("    url: http://www.gstatic.com/generate_204")
        lines.append("    interval: 300")
        lines.append("    proxies:")
        for n in names:
            lines.append(f"      - \"{n}\"")

    lines.append("")
    lines.append("rules:")
    rules = [
        ("DOMAIN-KEYWORD,adservice,REJECT",),
        ("DOMAIN-KEYWORD,guanggao,REJECT",),
        ("DOMAIN-SUFFIX,cn,DIRECT",),
        ("DOMAIN-KEYWORD,baidu,DIRECT",),
        ("DOMAIN-KEYWORD,alipay,DIRECT",),
        ("DOMAIN-KEYWORD,taobao,DIRECT",),
        ("DOMAIN-KEYWORD,alicdn,DIRECT",),
        ("DOMAIN-SUFFIX,bilibili.com,DIRECT",),
        ("DOMAIN-SUFFIX,qq.com,DIRECT",),
        ("DOMAIN-SUFFIX,tencent.com,DIRECT",),
        ("DOMAIN-SUFFIX,zhihu.com,DIRECT",),
        ("DOMAIN-SUFFIX,jd.com,DIRECT",),
        ("DOMAIN-KEYWORD,github,🚀 节点选择",),
        ("DOMAIN-KEYWORD,google,🚀 节点选择",),
        ("DOMAIN-KEYWORD,youtube,🚀 节点选择",),
        ("DOMAIN-KEYWORD,facebook,🚀 节点选择",),
        ("DOMAIN-KEYWORD,twitter,🚀 节点选择",),
        ("DOMAIN-KEYWORD,telegram,🚀 节点选择",),
        ("DOMAIN-SUFFIX,openai.com,🚀 节点选择",),
        ("DOMAIN-SUFFIX,anthropic.com,🚀 节点选择",),
        ("DOMAIN-SUFFIX,claude.ai,🚀 节点选择",),
        ("DOMAIN-SUFFIX,telegram.org,🚀 节点选择",),
        ("DOMAIN-SUFFIX,t.me,🚀 节点选择",),
        ("GEOIP,CN,DIRECT",),
        ("MATCH,🚀 节点选择",),
    ]
    for r in rules:
        lines.append(f"  - {r[0]}")

    return "\n".join(lines) + "\n"


def upload_file(filepath):
    """Upload file to hosting services, return URL or None."""
    services = [
        # tmpfiles.org
        {
            "url": "https://tmpfiles.org/api/v1/upload",
            "method": "form",
            "field": "file",
            "extract": lambda out: "https://tmpfiles.org/dl/" + out.split("/tmpfiles.org/")[1] if "/tmpfiles.org/" in out else None
            if isinstance(out, str) and "tmpfiles.org" in out else None,
        },
    ]

    for svc in services:
        try:
            cmd = ["curl", "-s", "--max-time", "15",
                   "-F", f"{svc['field']}=@{filepath}",
                   svc["url"]]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            if result.returncode == 0:
                output = result.stdout
                # Parse tmpfiles.org JSON response
                try:
                    data = json.loads(output)
                    if data.get("status") == "success":
                        url = data["data"]["url"]
                        # Convert view URL to direct download URL
                        dl_url = url.replace("tmpfiles.org/", "tmpfiles.org/dl/")
                        return dl_url
                except (json.JSONDecodeError, KeyError):
                    pass
        except Exception:
            continue

    return None


def main():
    parser = argparse.ArgumentParser(description="Merge proxy subscriptions into one Clash Meta config")
    parser.add_argument("--url", action="append", required=True, help="Subscription URL (can specify multiple)")
    parser.add_argument("--output", default=os.path.expanduser("~/merged_sub.yaml"), help="Output file path")
    parser.add_argument("--upload", action="store_true", help="Upload and return shareable URL")
    args = parser.parse_args()

    all_proxies = []
    for i, url in enumerate(args.url):
        prefix = f"S{i+1}"
        proxies = source_proxies(url, prefix)
        print(f"[OK] Source {i+1}: {len(proxies)} nodes from {url[:60]}...", file=sys.stderr)
        all_proxies.extend(proxies)

    if not all_proxies:
        print("[FAILED] No proxies found from any source", file=sys.stderr)
        sys.exit(1)

    # Filter out info-only nodes
    all_proxies = [p for p in all_proxies if p.get("server") not in ("127.0.0.1", "")]

    config = build_config(all_proxies)

    with open(args.output, "w") as f:
        f.write(config)

    print(f"[OK] Merged: {len(all_proxies)} nodes -> {args.output}", file=sys.stderr)

    if args.upload:
        url = upload_file(args.output)
        if url:
            print(f"[OK] Subscription URL: {url}")
        else:
            print("[FAILED] All upload services failed", file=sys.stderr)
            print(f"[INFO] File saved locally: {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
