---
name: happy-qr-auth
description: "happy CLI web auth with QR code display — bypasses TUI, generates scannable QR for phone camera, polls until authorized"
user-invocable: false
version: "1.0.0"
category: auth
tags: [happy, claude-mobile, qr, auth, terminal]
effort: medium
auto-generated: true
created: 2026-04-23
---

# Happy Qr Auth

## 场景
#!/usr/bin/env node
// happy web auth with QR code display
// Scan with phone camera → opens app.happy.engineering → approve → done

import { randomBytes } from 'node:crypto';
import { createRequire } from 'node:module';
import https from 'node:https';

const require = createRequire(import.meta.url);
const nacl = require('/mnt/pool-disks/POOL-D1/home-offload/.npm-global/lib/node_modules/happy/node_modules/tweetnacl/nacl-fast.js');
const qrcode = require('/mnt/pool-disks/POOL-D1/home-offload/.npm-global/lib/node_modules/happy/node_modules/qrcode-terminal/lib/main.js');

const SERVER = 'api.cluster-fluster.com';
const WEBAPP = 'https://app.happy.engineering';

function encodeBase64Url(buf) {
  return Buffer.from(buf).toString('base64').replaceAll('+', '-').replaceAll('/', '_').replaceAll('=', '');
}
function encodeBase64(buf) {
  return Buffer.from(buf).toString('base64');
}

async function post(path, body) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(body);
    const req = https.request({
      hostname: SERVER, path, method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': data.length, 'X-Happy-Client': 'cli/1.1.7' }
    }, res => {
      let s = '';
      res.on('data', d => s += d);
      res.on('end', () => resolve({ status: res.statusCode, data: JSON.parse(s) }));
    });
    req.on('error', reject);
    req.write(data);
    req.end();
  });
}

async function delay(ms) { return new Promise(r => setTimeout(r, ms)); }

async function main() {
  const secret = new Uint8Array(randomBytes(32));
  const kp = nacl.box.keyPair.fromSecretKey(secret);
  const pubB64 = encodeBase64(kp.publicKey);
  const pubB64url = encodeBase64Url(kp.publicKey);

  // Register auth request
  const reg = await post('/v1/auth/request', { publicKey: pubB64, supportsV2: true });
  if (reg.status !== 200) {
    console.error('注册失败:', reg.data);
    process.exit(1);
  }

  const webUrl = `${WEBAPP}/terminal/connect#key=${pubB64url}`;
  console.log('\n📱 用手机扫描二维码完成 Happy 授权\n');
  console.log('='.repeat(60));
  qrcode.generate(webUrl, { small: true });
  console.log('='.repeat(60));
  console.log('\n或手动打开:\n' + webUrl + '\n');
  console.log('等待授权中...');

  // Poll
  let dots = 0;
  while (true) {
    await delay(2000);
    try {
      const r = await post('/v1/auth/request', { publicKey: pubB64, supportsV2: true });
      if (r.data.state === 'authorized') {
        // Save credentials (legacy format)
        const fs = await import('node:fs/promises');
        const os = await import('node:os');
        const path = await import('node:path');
        const credPath = path.join(os.homedir(), '.happy', 'credentials.json');
        const cred = { token: r.data.token, publicKey: pubB64, version: 1 };
        await fs.mkdir(path.join(os.homedir(), '.happy'), { recursive: true });
        await fs.writeFile(credPath, JSON.stringify(cred, null, 2));
        console.log('\n\n✓ 授权成功！凭证已保存到 ~/.happy/credentials.json\n');
        process.exit(0);
      }
    } catch (e) {
      // ignore poll errors, retry
    }
    process.stdout.write('\r等待授权' + '.'.repeat(dots % 4 + 1) + '   ');
    dots++;
  }
}

main().catch(e => { console.error(e); process.exit(1); });

## 步骤
See content summary.

## 注意事项
Auto-generated from brief summary.
