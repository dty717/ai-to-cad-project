const http = require('http');

const LISTEN_PORT = 27183;
const TARGET_HOST = '127.0.0.1';
const TARGET_PORT = 27182; // Fusion 360 internal port

let activeSessionId = null; // Automatically store active session ID

const server = http.createServer((req, res) => {
    // CORS headers (allowing and exposing MCP-Session-Id)
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

    const forwardHeaders = { ...req.headers };
    forwardHeaders.host = `${TARGET_HOST}:${TARGET_PORT}`;

    // Strip browser security headers that Fusion's local endpoint may reject.
    delete forwardHeaders.origin;
    delete forwardHeaders.referer;
    delete forwardHeaders['sec-fetch-mode'];
    delete forwardHeaders['sec-fetch-site'];
    delete forwardHeaders['sec-fetch-dest'];

    // Reuse the active MCP session if the caller omits its session header.
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
});

// Keep this proxy bound to loopback; do not expose this unauthenticated script-execution bridge to a network.
server.listen(LISTEN_PORT, '127.0.0.1', () => {
    console.log(`[MCP HTTP Proxy] Listening on 127.0.0.1:${LISTEN_PORT} -> Forwarding to ${TARGET_HOST}:${TARGET_PORT}`);
});
