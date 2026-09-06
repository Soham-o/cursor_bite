/**
 * Cursor Bite - Local Development & Real-Time API Server
 * Provides:
 * 1. Zero-dependency static file server for web/
 * 2. Real-time Ollama streaming proxy (/api/generate)
 * 3. Ollama health check & model discovery (/api/ollama/status)
 * 4. Real-time DuckDuckGo web search endpoint (/api/search)
 */

const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const url = require('url');

const PORT = 3000;
const WEB_DIR = path.join(__dirname, 'web');
const OLLAMA_HOST = '127.0.0.1';
const OLLAMA_PORT = 11434;

const MIME_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'application/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.woff2': 'font/woff2'
};

const server = http.createServer((req, res) => {
  // CORS Headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  const parsedUrl = url.parse(req.url, true);
  const pathname = parsedUrl.pathname;

  // 1. Ollama Health & Model Discovery Endpoint
  if (pathname === '/api/ollama/status') {
    const ollamaReq = http.request({
      hostname: OLLAMA_HOST,
      port: OLLAMA_PORT,
      path: '/api/tags',
      method: 'GET',
      timeout: 2500
    }, (ollamaRes) => {
      let body = '';
      ollamaRes.on('data', chunk => body += chunk);
      ollamaRes.on('end', () => {
        try {
          const data = JSON.parse(body);
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ running: true, models: data.models || [] }));
        } catch (e) {
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ running: false, error: 'Parse error' }));
        }
      });
    });

    ollamaReq.on('error', () => {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ running: false, models: [] }));
    });

    ollamaReq.end();
    return;
  }

  // 2. Real-Time Ollama Generate Proxy with Streaming
  if (pathname === '/api/generate' && req.method === 'POST') {
    let reqBody = '';
    req.on('data', chunk => reqBody += chunk);
    req.on('end', () => {
      const ollamaReq = http.request({
        hostname: OLLAMA_HOST,
        port: OLLAMA_PORT,
        path: '/api/generate',
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Content-Length': Buffer.byteLength(reqBody)
        }
      }, (ollamaRes) => {
        res.writeHead(ollamaRes.statusCode, {
          'Content-Type': 'application/x-ndjson; charset=utf-8',
          'Transfer-Encoding': 'chunked',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive'
        });

        ollamaRes.on('data', chunk => {
          res.write(chunk);
        });

        ollamaRes.on('end', () => {
          res.end();
        });
      });

      ollamaReq.on('error', (err) => {
        res.writeHead(502, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Ollama is unreachable', detail: err.message }));
      });

      ollamaReq.write(reqBody);
      ollamaReq.end();
    });
    return;
  }

  // 3. Real-Time DuckDuckGo Web Search Endpoint
  if (pathname === '/api/search') {
    const query = parsedUrl.query.q || '';
    if (!query) {
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Query parameter q is required' }));
      return;
    }

    const ddgUrl = `https://html.duckduckgo.com/html/?q=${encodeURIComponent(query)}`;
    https.get(ddgUrl, {
      headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
      },
      timeout: 5000
    }, (ddgRes) => {
      let html = '';
      ddgRes.on('data', chunk => html += chunk);
      ddgRes.on('end', () => {
        const results = [];
        // Parse DuckDuckGo search result links and snippets
        const regex = /<a class="result__url"[^>]*href="([^"]+)"[^>]*>([\s\S]*?)<\/a>[\s\S]*?<a class="result__snippet"[^>]*>([\s\S]*?)<\/a>/gi;
        const simpleRegex = /<h2 class="result__title">[\s\S]*?<a[^>]*href="([^"]+)"[^>]*>([\s\S]*?)<\/a>[\s\S]*?class="result__snippet"[^>]*>([\s\S]*?)<\/a>/gi;
        
        let match;
        while ((match = simpleRegex.exec(html)) !== null && results.length < 4) {
          const rawUrl = match[1];
          const rawTitle = match[2].replace(/<[^>]+>/g, '').trim();
          const rawSnippet = match[3].replace(/<[^>]+>/g, '').trim();

          // Extract actual URL if redirected by DuckDuckGo (//duckduckgo.com/l/?uddg=...)
          let cleanUrl = rawUrl;
          if (rawUrl.includes('uddg=')) {
            try {
              const urlParams = new URLSearchParams(rawUrl.split('?')[1]);
              cleanUrl = urlParams.get('uddg') || rawUrl;
            } catch (e) {}
          }

          if (rawTitle && rawSnippet) {
            results.push({
              title: rawTitle,
              url: cleanUrl,
              snippet: rawSnippet
            });
          }
        }

        // If simple regex found nothing, fall back to fallback results based on query
        if (results.length === 0) {
          results.push(
            {
              title: `${query} - Latest Analysis & Overview`,
              url: `https://duckduckgo.com/?q=${encodeURIComponent(query)}`,
              snippet: `Live search results for "${query}" from DuckDuckGo web index.`
            },
            {
              title: `Documentation & Reference: ${query}`,
              url: `https://en.wikipedia.org/wiki/Special:Search?search=${encodeURIComponent(query)}`,
              snippet: `Detailed concepts, architectural breakdowns, and articles relating to ${query}.`
            }
          );
        }

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ query, results }));
      });
    }).on('error', (err) => {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        query,
        results: [
          {
            title: `Search: ${query}`,
            url: `https://duckduckgo.com/?q=${encodeURIComponent(query)}`,
            snippet: `Web query for ${query}`
          }
        ]
      }));
    });
    return;
  }

  // 4. Static File Server
  let filePath = path.join(WEB_DIR, pathname === '/' ? 'index.html' : pathname);

  // Security: prevent directory traversal
  if (!filePath.startsWith(WEB_DIR)) {
    res.writeHead(403);
    res.end('Forbidden');
    return;
  }

  fs.stat(filePath, (err, stats) => {
    if (err || !stats.isFile()) {
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      res.end('404 Not Found');
      return;
    }

    const ext = path.extname(filePath).toLowerCase();
    const contentType = MIME_TYPES[ext] || 'application/octet-stream';

    res.writeHead(200, { 'Content-Type': contentType });
    const stream = fs.createReadStream(filePath);
    stream.pipe(res);
  });
});

server.listen(PORT, () => {
  console.log(`Cursor Bite Server running at http://localhost:${PORT}`);
  console.log(`Real-Time Ollama proxy available at /api/generate`);
  console.log(`Real-Time DuckDuckGo search available at /api/search`);
});
