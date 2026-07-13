const puppeteer = require('puppeteer-core');
const http = require('http');
const PC_CHROME_URL = 'http://localhost:9222';

async function getBrowser() {
  try {
    const resp = await fetch(PC_CHROME_URL + '/json/version');
    const info = await resp.json();
    return await puppeteer.connect({
      browserWSEndpoint: info.webSocketDebuggerUrl,
      defaultViewport: null
    });
  } catch(e) {
    throw new Error('Cannot connect to PC Chrome: ' + e.message);
  }
}

const s = http.createServer(async(req, res) => {
  try {
    const u = new URL(req.url, 'http://localhost');
    res.setHeader('Access-Control-Allow-Origin', '*');
    if (u.pathname === '/browse') {
      const target = u.searchParams.get('url') || 'https://www.baidu.com';
      const b = await getBrowser();
      const page = await b.newPage();
      await page.goto(target, {timeout: 20000, waitUntil: 'domcontentloaded'});
      const title = await page.title();
      const text = await page.evaluate(() => document.body?.innerText?.substring(0, 5000) || '');
      const html = await page.content();
      await page.close();
      res.writeHead(200, {'Content-Type': 'application/json'});
      res.end(JSON.stringify({title, text, html_length: html.length, status: 'ok'}));
    } else if (u.pathname === '/screenshot') {
      const target = u.searchParams.get('url') || 'https://www.baidu.com';
      const b = await getBrowser();
      const page = await b.newPage();
      await page.setViewport({width: 1280, height: 720});
      await page.goto(target, {timeout: 20000, waitUntil: 'networkidle2'});
      const buf = await page.screenshot({type: 'png', fullPage: false});
      await page.close();
      res.writeHead(200, {'Content-Type': 'image/png'});
      res.end(buf);
    } else if (u.pathname === '/pdf') {
      const target = u.searchParams.get('url') || 'https://www.baidu.com';
      const b = await getBrowser();
      const page = await b.newPage();
      await page.goto(target, {timeout: 20000, waitUntil: 'networkidle2'});
      const buf = await page.pdf({format: 'A4'});
      await page.close();
      res.writeHead(200, {'Content-Type': 'application/pdf'});
      res.end(buf);
    } else if (u.pathname === '/health') {
      try {
        const resp = await fetch(PC_CHROME_URL + '/json/version');
        const info = await resp.json();
        res.writeHead(200, {'Content-Type': 'application/json'});
        res.end(JSON.stringify({status: 'ok', browser: info.Browser}));
      } catch(e) {
        res.writeHead(503, {'Content-Type': 'application/json'});
        res.end(JSON.stringify({status: 'error', error: e.message}));
      }
    } else {
      res.writeHead(200, {'Content-Type': 'text/plain'});
      res.end('Headless Browser API\nGET /browse?url=xxx\nGET /screenshot?url=xxx\nGET /pdf?url=xxx\nGET /health');
    }
  } catch(e) {
    res.writeHead(500, {'Content-Type': 'application/json'});
    res.end(JSON.stringify({error: e.message}));
  }
});

s.listen(9922, '0.0.0.0', () => {
  console.log('Headless Browser API :9922 -> ' + PC_CHROME_URL);
});
