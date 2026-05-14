# Hosting `meta-data-mcp` as a remote SSE server

This guide walks through deploying `meta-data-mcp` on your own server so that
remote MCP clients (Claude Desktop, Claude Code, Cursor, Windsurf, Gemini CLI,
LM Studio, etc.) can connect over HTTPS without each user spawning the server
locally.

The supported architecture is:

```
   MCP client                       Your server
   (Claude Desktop, etc.)
        │
        │  HTTPS + Authorization: Bearer <token>
        ▼
   ┌─────────────────┐   loopback   ┌──────────────────────────┐
   │  Reverse proxy  │ ───────────► │ meta-data-mcp (SSE)      │
   │  (Caddy / nginx │              │ 127.0.0.1:8000           │
   │  / Cloudflare)  │              │ stdio-style transport in │
   │                 │              │ both directions          │
   └─────────────────┘              └──────────────────────────┘
        ▲
        │  TLS termination + (optional) extra auth layer
        │
   Public internet
```

The server itself only listens on `127.0.0.1`. TLS and the outermost network
boundary belong to a reverse proxy you control. Authentication is enforced by
a built-in bearer-token middleware (see [Authentication](#authentication)).

---

## 1. Install on the host

```bash
# As an unprivileged user on the host (e.g. an Ubuntu droplet)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv tool install meta-data-mcp
# or, from source:
git clone https://github.com/derekslinz/meta-data-mcp.git
cd meta-data-mcp
uv sync
```

Verify:

```bash
meta-data-mcp version
```

## 2. Set the bearer token

The server only requires authentication when the
`META_DATA_MCP_AUTH_TOKEN` environment variable is set. Generate a long
random secret and store it somewhere stable (a systemd `EnvironmentFile`, a
1Password CLI lookup, or your secret manager of choice):

```bash
openssl rand -hex 32
# → e.g. 9e2f...5a1c (paste this into your env file)
```

When the env var is **unset**, the server logs:

```
SSE bearer auth DISABLED — set META_DATA_MCP_AUTH_TOKEN to require
Authorization: Bearer <token> on /sse and /messages
```

and serves SSE traffic without authentication. This is fine for local
development on `127.0.0.1`, but is **not safe for public hosting**. The
sections below assume you've set the variable.

## 3. Run the server bound to localhost

```bash
export META_DATA_MCP_AUTH_TOKEN="$(cat /etc/meta-data-mcp/token)"
meta-data-mcp run --transport sse --host 127.0.0.1 --port 8000
```

On startup you should see:

```
SSE bearer auth enabled (META_DATA_MCP_AUTH_TOKEN set;
protecting /sse and /messages)
Uvicorn running on http://127.0.0.1:8000
```

### systemd unit (recommended)

`/etc/systemd/system/meta-data-mcp.service`:

```ini
[Unit]
Description=meta-data-mcp SSE server
After=network-online.target

[Service]
Type=simple
User=mcp
EnvironmentFile=/etc/meta-data-mcp/env
ExecStart=/home/mcp/.local/bin/meta-data-mcp run --transport sse \
    --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

`/etc/meta-data-mcp/env` (mode `0600`, owner `mcp:mcp`):

```
META_DATA_MCP_AUTH_TOKEN=...your generated hex...
OPENDATA_MCP_CONTACT=ops@yourdomain.example
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now meta-data-mcp
sudo systemctl status meta-data-mcp
```

## 4. Put TLS in front (Caddy example)

The smallest practical Caddy config (`/etc/caddy/Caddyfile`):

```caddyfile
mcp.linzalytics.com {
    reverse_proxy 127.0.0.1:8000 {
        # SSE keeps connections open for hours; bump the proxy timeouts.
        flush_interval -1
        transport http {
            keepalive 5m
            response_header_timeout 0
        }
    }
}
```

Caddy will issue and renew a Let's Encrypt cert automatically as long as
`mcp.linzalytics.com` resolves to your server. Reload with
`sudo systemctl reload caddy`.

> The `flush_interval -1` directive disables response buffering so SSE
> chunks reach the client immediately. Without it, clients see large
> latency spikes and eventual hangs.

### Health check

`/` is intentionally **not** behind the bearer-token middleware so that
uptime monitoring works:

```bash
curl -sS https://mcp.linzalytics.com/ | jq
# → {"status":"running","server":"meta-data-mcp","transport":"sse",...}
```

`/sse` and `/messages` return `401 Unauthorized` without a valid bearer
token:

```bash
curl -sS https://mcp.linzalytics.com/sse -i | head -3
# → HTTP/2 401
# → www-authenticate: Bearer realm="meta-data-mcp"
```

## 5. Wire a client to the hosted server

Run on **your laptop** (not the server):

```bash
META_DATA_MCP_AUTH_TOKEN=<the-same-token> meta-data-mcp setup --print-json
```

The stdout of that command is a JSON snippet for the **local stdio**
launcher (still useful as a fallback). The interesting part is on
**stderr**, where the command surfaces the SSE client snippet you'll
actually paste into the remote-client config:

```jsonc
{
  "meta-data-mcp": {
    "url": "https://YOUR-HOST/sse",
    "headers": {
      "Authorization": "Bearer <the-same-token>"
    }
  }
}
```

Replace `YOUR-HOST` with your hostname (e.g. `mcp.linzalytics.com`) and
paste the result into:

| Client | Where to paste |
|---|---|
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` under `mcpServers` |
| Claude Code | `~/.claude.json` under `mcpServers` |
| Cursor | `~/.cursor/mcp.json` under `mcpServers` |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` under `mcpServers` |
| Gemini CLI | `~/.gemini/settings.json` under `mcpServers` |
| LM Studio | In-app MCP settings UI |

Restart the client. It will connect to your server, send the token on
every request, and see all 66 meta-data-mcp tools just as if the server
were running locally.

## Authentication

| Property | Value |
|---|---|
| Mechanism | `Authorization: Bearer <token>` HTTP header |
| Token source | `META_DATA_MCP_AUTH_TOKEN` environment variable on the server |
| Protected paths | `/sse`, `/messages` |
| Unprotected paths | `/` (health check) |
| Failure response | `401` with `WWW-Authenticate: Bearer realm="meta-data-mcp"` |
| Token comparison | `hmac.compare_digest` (constant-time) |
| Number of tokens | One per server instance (rotate by restarting with a new value) |
| OAuth / per-user tokens | **Not** supported — see [Threat model](#threat-model) |

### Threat model

`meta-data-mcp` exposes ~66 read-only public-data providers (NASA, NOAA,
OSM, SEC EDGAR, Crossref, …). Nothing the server returns is sensitive on
its own; the data is already public via the upstream APIs. What the
bearer token defends against is:

- **Abuse / DoS** of your compute and bandwidth budget.
- **Shared rate-limit exhaustion** against upstream APIs that throttle
  per-IP (SEC EDGAR, OpenAlex, Overpass).
- **Outbound UA / contact reputation** — many upstreams require an
  identifying User-Agent (`OPENDATA_MCP_CONTACT`) and may ban abusers.

For a single operator (you) and a handful of MCP clients, a single
shared bearer token is the right tool. If you ever need per-user
revocation or audit trails, front the server with Cloudflare Access or
similar — it adds SSO + audit without code changes.

### Rotating the token

```bash
NEW=$(openssl rand -hex 32)
sudo tee /etc/meta-data-mcp/env >/dev/null <<EOF
META_DATA_MCP_AUTH_TOKEN=$NEW
OPENDATA_MCP_CONTACT=ops@yourdomain.example
EOF
sudo systemctl restart meta-data-mcp
# Update each client's headers to send the new value.
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `401 Unauthorized` from your own client | Token mismatch between server env and client header | Re-copy the token; verify with `curl -H "Authorization: Bearer $TOKEN" https://host/sse` |
| SSE connects then drops every 60 s | Reverse proxy idle/read timeout too low | Disable response timeout in Caddy/nginx (see Caddy snippet above) |
| Client never sees tools | Client doesn't support remote SSE | Use `setup --client <name>` with the local stdio snippet instead |
| `unauthorized` on `/sse` despite valid header | CORS preflight stripped the header | Already handled — CORS middleware sits outermost; confirm proxy doesn't drop `Authorization` |
| Server warning `auth DISABLED` on startup | `META_DATA_MCP_AUTH_TOKEN` not visible to the process | Verify with `sudo systemctl show meta-data-mcp -p Environment`; reload if you edited the env file |
