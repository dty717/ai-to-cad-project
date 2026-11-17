const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');

// Optional: define keyPath directly here, or let config.js define it:
// const keyPath = './privkey.pem';

// Optional: load from config.js if it exists
try {
  global.keyPath = require('./config').keyPath;
} catch (e) {
  // If config.js is missing or null, do nothing
}

const LISTEN_HOST = '0.0.0.0';
const HTTP_PORT = 27183;
const HTTPS_PORT = 27184;
const TARGET_HOST = '127.0.0.1';
const TARGET_PORT = 27182; // Fusion 360 internal port

let activeSessionId = null;

// Proxy request handler
const handleRequest = (req, res) => {
  const corsHeaders = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, Accept, x-requested-with, MCP-Session-Id, mcp-session-id',
    'Access-Control-Expose-Headers': 'MCP-Session-Id, mcp-session-id',
    'Access-Control-Max-Age': '86400'
  };

  if (req.method === 'OPTIONS') {
    res.writeHead(204, corsHeaders);
    res.end();
    return;
  }

  // Health-check / certificate acceptance route for Safari on iPhone
  if (req.method === 'GET' && (req.url === '/' || req.url === '/mcp')) {
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8', ...corsHeaders });
    res.end('<h3>Fusion MCP Proxy is active!</h3><p>HTTPS certificate is trusted.</p>');
    return;
  }

  const forwardHeaders = { ...req.headers };
  forwardHeaders.host = `${TARGET_HOST}:${TARGET_PORT}`;

  delete forwardHeaders.origin;
  delete forwardHeaders.referer;
  delete forwardHeaders['sec-fetch-mode'];
  delete forwardHeaders['sec-fetch-site'];
  delete forwardHeaders['sec-fetch-dest'];

  const incomingSessionId = req.headers['mcp-session-id'] || req.headers['MCP-Session-Id'];
  if (incomingSessionId) {
    activeSessionId = incomingSessionId;
    forwardHeaders['mcp-session-id'] = incomingSessionId;
  } else if (activeSessionId) {
    forwardHeaders['mcp-session-id'] = activeSessionId;
  }

  const options = {
    hostname: TARGET_HOST,
    port: TARGET_PORT,
    path: req.url,
    method: req.method,
    headers: forwardHeaders
  };

  const proxyReq = http.request(options, (proxyRes) => {
    const newSessionId = proxyRes.headers['mcp-session-id'] || proxyRes.headers['MCP-Session-Id'];
    if (newSessionId) {
      activeSessionId = newSessionId;
      console.log(`[Proxy] Captured Session ID: ${activeSessionId}`);
    }

    console.log(`[Proxy] ${req.method} ${req.url} -> Status: ${proxyRes.statusCode}`);
    res.writeHead(proxyRes.statusCode, { ...proxyRes.headers, ...corsHeaders });
    proxyRes.pipe(res, { end: true });
  });

  proxyReq.on('error', (err) => {
    console.error(`[Proxy Error] ${err.message}`);
    res.writeHead(502, { 'Content-Type': 'application/json', ...corsHeaders });
    res.end(JSON.stringify({ error: 'Proxy Gateway Error', details: err.message }));
  });

  req.pipe(proxyReq, { end: true });
};

// 1. Always start HTTP server on 27183 (for PC)
const httpServer = http.createServer(handleRequest);
httpServer.listen(HTTP_PORT, LISTEN_HOST, () => {
  console.log(`[Proxy HTTP]  Listening on http://${LISTEN_HOST}:${HTTP_PORT} -> http://${TARGET_HOST}:${TARGET_PORT}`);
});

// 2. Use try...catch to judge if keyPath is defined
try {
  if (keyPath) {
    // Helper to find certificate file matching keyPath
    const findCertFile = (kp) => {
      const dir = path.dirname(kp);
      const candidates = [
        // Check privkey -> fullchain FIRST (before replacing 'key')
        kp.replace(/privkey/i, 'fullchain'),
        kp.replace(/privkey/i, 'cert'),
        kp.replace(/key/i, 'cert'),
        kp.replace(/\.key$/i, '.crt'),
        // Common cert names in the same directory
        path.join(dir, 'fullchain.pem'),
        path.join(dir, 'cert.pem')
      ];
      for (const cand of candidates) {
        if (cand !== kp && fs.existsSync(cand)) return cand;
      }
      return null;
    };

    const key = fs.readFileSync(keyPath);
    const certPath = findCertFile(keyPath);
    let cert;

    if (certPath) {
      cert = fs.readFileSync(certPath);
    } else if (key.toString().includes('-----BEGIN CERTIFICATE-----')) {
      cert = key; // Combined PEM with both key and cert
    } else {
      throw new Error(`No certificate found for "${keyPath}". Expected fullchain.pem or cert.pem.`);
    }

    const httpsServer = https.createServer({ key, cert }, handleRequest);
    httpsServer.listen(HTTPS_PORT, LISTEN_HOST, () => {
      console.log(`[Proxy HTTPS] Listening on https://${LISTEN_HOST}:${HTTPS_PORT} -> http://${TARGET_HOST}:${TARGET_PORT}`);
      console.log(`[Proxy HTTPS] Using key: ${keyPath}`);
      console.log(`[Proxy HTTPS] Using cert: ${certPath || keyPath}`);
    });
  }
} catch (e) {
  // Catches `ReferenceError: keyPath is not defined` or cert loading errors
  console.log(`[Proxy HTTPS] ${e.message}. Running HTTP only.`);
}