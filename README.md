# IPovtich

```text


                    .-._   _ _ _ _ _ _ _ _
         .-''-.__.-'00  '-' ' ' ' ' ' ' ' '-.
         '.___ '    .   .--_'-' '-' '-' _'-' '._
       DLL : V 'vv-'   '_   '.       .'  _..' '.'.
            '=.____.=_.--'   :_.__.__:_   '.   : :
                    (((____.-'        '-.  /   : :
                                      (((-'\ .' /
                                    _____..'  .'
                                   '-._____.-'
      ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
                  I P O V T I C H  ·  b y  K R O K O D L L
      ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
```

Visualise Nmap (XML, gnmap) and tabular host data as an interactive network topology graph. Local-first by default: no cloud, no API key required.

**Stack:** FastAPI, React, React Flow, TypeScript. **UI:** English and French.

## Summary

- Parse scan exports and tables, build a graph in the browser.
- Runs on your machine; optional environment variables harden the API for shared or internet-facing deployments.
- REST API under `/v1` (for example `POST /v1/parse/nmap`). OpenAPI UI at `/docs` when enabled.

## Requirements

| Tool    | Version   |
|---------|-----------|
| Python  | 3.11+     |
| Node.js | 20 LTS+   |

## Quick start

**API**

```bash
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --host 127.0.0.1 --port 8001
```

**Web UI**

```bash
cd frontend && npm ci && npm run dev
```

Open the URL printed by Vite (usually `http://127.0.0.1:5173`).

**Sanity check**

```bash
curl -s http://127.0.0.1:8001/health
```

Expect `{"status":"ok"}`.

Sample input: `data/nmap_minimal.xml`.

## Configuration

For on-premise installs, copy `backend/.env.example` to `backend/.env` and `frontend/.env.example` to `frontend/.env.local` (or `.env`), then set values. Comments in each file list variables; never commit real secrets.

### Backend (optional)

| Variable | Purpose |
|----------|---------|
| `MAX_UPLOAD_BYTES` | Upload cap (default 10 MiB, max 100 MiB). |
| `CORS_ORIGINS` | Comma-separated full origins (e.g. `https://app.example.com`). `*` is rejected. Default includes Vite on port 5173. |
| `IPOVITCH_API_KEY` | Optional static key via `Authorization: Bearer` or `X-Api-Key` on `/v1/*`. Prefer JWT in the browser (no secret in the bundle). |
| `IPOVITCH_JWT_SECRET` | At least 32 characters. Signs access tokens after login. Use with `IPOVITCH_LOGIN_PASSWORD` or `IPOVITCH_LOGIN_PASSWORD_HASH`. |
| `IPOVITCH_LOGIN_PASSWORD` | Shared password for `POST /v1/auth/token` (dev / small teams). Production: prefer `IPOVITCH_LOGIN_PASSWORD_HASH` (bcrypt). |
| `IPOVITCH_LOGIN_PASSWORD_HASH` | Bcrypt hash of the dashboard password. |
| `IPOVITCH_JWT_TTL_SECONDS` | Token lifetime (default 8h, min 60s, max 7 days). |
| `IPOVITCH_OPENAPI_ENABLED` | Set to `0`, `false`, or `off` to disable `/docs`, `/redoc`, and `/openapi.json` in production. |
| `IPOVITCH_RATE_LIMIT_PER_MINUTE` | Per-IP limit on all routes (including `/health`). Omit for unlimited (typical locally). |
| `IPOVITCH_LOGIN_RATE_PER_MINUTE` | Per-IP limit on `POST /v1/auth/token` only (default 20). `0` disables (not recommended on the public internet). Max 500. |
| `IPOVITCH_HSTS_MAX_AGE` | If set (seconds), sends `Strict-Transport-Security`. Use only when the API is served over HTTPS end-to-end. |

### Frontend (optional)

| Variable | Purpose |
|----------|---------|
| `VITE_API_BASE` | API origin (no path suffix). The UI calls that host under `/v1/...`. Must be `http://` or `https://` without credentials. |
| `VITE_API_KEY` | Same value as `IPOVITCH_API_KEY`, embedded at build time (not secret). Prefer UI login and JWT in `sessionStorage` when the API exposes `POST /v1/auth/token`. |

## Authentication

The API can issue short-lived JWTs after a password check; the browser stores the token in `sessionStorage`. That pattern is similar in spirit to [SysReptor](https://docs.sysreptor.com/) API tokens. Built-in OIDC or enterprise SSO is not included: use a reverse proxy (Authelia, OAuth2 Proxy, Cloudflare Access, etc.) if you need an IdP.

## Security notes

- Response headers include `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, and `Cache-Control: no-store` on `/v1`, `/docs`, and OpenAPI.
- JWTs use fixed `iss` / `aud` and required claims. Login password length is capped. `POST /v1/auth/token` is rate-limited per IP. Oversized bodies are rejected early via `Content-Length` (also set `client_max_body_size` on your reverse proxy).
- The SPA does not render user graph data with `dangerouslySetInnerHTML`. A JWT in `sessionStorage` is still exposed if XSS exists: use CSP and keep dependencies patched for high-threat deployments.
- Do not expose the API without TLS on untrusted networks.

## Production checklist

1. Bind Uvicorn to loopback or a private interface, or terminate TLS at nginx, Caddy, or Traefik.
2. Prefer `IPOVITCH_JWT_SECRET` and `IPOVITCH_LOGIN_PASSWORD_HASH`, plus `IPOVITCH_OPENAPI_ENABLED=0`. Set `IPOVITCH_RATE_LIMIT_PER_MINUTE` (e.g. `120`). Reserve `IPOVITCH_API_KEY` for non-browser clients if needed.
3. Set `CORS_ORIGINS` to your real UI origins only.
4. Behind a proxy, configure trusted forwarded headers if rate limits use client IP; otherwise every client may look like the proxy.
5. Treat `VITE_API_KEY` as a convenience for local automation, not confidentiality.

## Development

**Backend**

```bash
cd backend && source .venv/bin/activate && ruff check app tests && pytest
```

`app/` is covered at 100% line coverage in CI.

**Frontend**

```bash
cd frontend && npm run lint && npm test && npm run build
```

## Repository layout

| Path | Contents |
|------|----------|
| `backend/app/` | API, parsers, models |
| `backend/tests/` | Pytest and fixtures |
| `frontend/src/` | UI, graph layout, API client |

Dependabot opens grouped npm updates (production vs development). Keep `package-lock.json` committed and review major bumps (React Flow, jsPDF, etc.) explicitly.

## Author

[KROKODLL](https://github.com/KROKODLL)

## License

[MIT](LICENSE)
