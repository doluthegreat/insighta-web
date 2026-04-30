# insighta-web

> The browser interface for Insighta Labs+. A server-rendered web portal that gives non-technical users access to profile intelligence through a clean, authenticated UI — with the same data and rules as the CLI.

---

## About

Insighta Labs+ is used by multiple teams — analysts who are not comfortable with a terminal, engineers who want a visual overview, and stakeholders who just need to see the data. This web portal is built for all of them.

It connects to the same backend as the CLI. There is no separate API, no separate database, no separate auth system. Log in through GitHub, and the same role-based access rules apply whether you're on the web or in a terminal.

Security is handled properly for the browser context: tokens are stored in HttpOnly cookies that JavaScript cannot touch, CSRF protection is applied to every mutating request, and the refresh flow runs transparently in the background.

---

## System Architecture

```
insighta-web
├── src/
│   └── app.js              # Express app — serves pages, proxies API, handles auth cookies
├── public/
│   ├── css/
│   │   └── styles.css      # Styles
│   └── js/
│       └── app.js          # Client-side JS — CSRF token attachment, table rendering
└── views/                  # HTML templates (or server-rendered pages)
    ├── login.html
    ├── dashboard.html
    ├── profiles.html
    ├── profile-detail.html
    ├── search.html
    └── account.html
```

**How requests flow:**

```
Browser
  └── GET /login
        └── click "Continue with GitHub"
              └── GET /auth/github (backend)
                    └── 302 → GitHub OAuth
                          └── user approves
                                └── GET /auth/github/callback (backend)
                                      └── tokens issued as HttpOnly cookies
                                            └── 302 → /auth/callback (web portal)
                                                  └── browser now has:
                                                        access_token  (HttpOnly, JS-inaccessible)
                                                        refresh_token (HttpOnly, JS-inaccessible)
                                                        csrf_token    (readable by JS for header injection)
                                                  └── redirect to /dashboard

  └── GET /api/profiles (from dashboard)
        └── access_token cookie sent automatically by browser
        └── JS reads csrf_token cookie, adds X-CSRF-Token header
        └── Backend validates both, returns data
```

---

## Authentication Flow

The web portal delegates the entire OAuth handshake to the backend. It does not implement its own GitHub OAuth — it redirects the browser to `GET /auth/github` on the backend, which handles state generation, PKCE, the GitHub redirect, code exchange, and token issuance.

When the backend finishes, it sets three cookies on the browser and redirects to `/auth/callback` on the web portal:

| Cookie | HttpOnly | Purpose |
|--------|----------|---------|
| `access_token` | ✅ Yes | JWT sent automatically on every request to the backend |
| `refresh_token` | ✅ Yes | Used to silently refresh the access token when it expires |
| `csrf_token` | ❌ No | Read by JavaScript and sent as `X-CSRF-Token` header on mutations |

**Why HttpOnly for access and refresh tokens?** A JavaScript-accessible token can be stolen by XSS. An HttpOnly cookie cannot be read by any script — it is only transmitted by the browser automatically on matching requests. This means even a successful XSS attack cannot exfiltrate the session tokens.

**Why is `csrf_token` not HttpOnly?** Because it needs to be readable by JavaScript. The Double-Submit Cookie pattern works by requiring the client to prove it can read the cookie — something a cross-origin attacker cannot do due to the Same-Origin Policy. JS reads `csrf_token`, puts it in the `X-CSRF-Token` request header, and the backend compares header value against cookie value. If they don't match, the request is rejected with 403.

---

## Token Handling

| | Access token | Refresh token |
|--|--|--|
| **Lifetime** | 3 minutes | 5 minutes |
| **Stored** | HttpOnly cookie | HttpOnly cookie |
| **JS accessible** | No | No |
| **Refresh trigger** | 401 from backend | — |

When the access token expires, the web portal's client-side JS (or server-side middleware) calls `POST /auth/refresh` with the refresh token cookie. The backend validates the refresh token, invalidates it (single-use rotation), and issues a new pair set as new cookies. The original request is retried transparently.

If the refresh token is also expired, the user is redirected to `/login`.

---

## Role Enforcement

Roles are enforced on the **backend**. The web portal reflects them in the UI — admin users see Create and Delete controls, analyst users do not. But these are UI hints only. If an analyst somehow calls a write endpoint, the backend still returns 403.

| Feature | admin | analyst |
|---------|-------|---------|
| View profiles list | ✅ | ✅ |
| View profile detail | ✅ | ✅ |
| Search profiles | ✅ | ✅ |
| Export CSV | ✅ | ✅ |
| Create profile button | ✅ (visible) | ❌ (hidden) |
| Delete profile button | ✅ (visible) | ❌ (hidden) |

The current user's role is read from `GET /auth/me` on page load and stored in memory (never in `localStorage` or a cookie the user can edit).

---

## Natural Language Search

The search page sends the user's plain-text input to `GET /api/profiles/search?q=` on the backend. No parsing happens in the web portal — the backend's `parse_nl()` function handles all interpretation.

Supported query patterns (parsed server-side):

```
"young males from nigeria"    → gender=male, min_age=16, max_age=24, country_id=NG
"adult females over 30"       → gender=female, age_group=adult, min_age=30
"seniors in the united kingdom" → age_group=senior, country_id=GB
```

Results are rendered in the same paginated table as the profiles list.

---

## Pages

| Route | Description | Auth required |
|-------|-------------|---------------|
| `/login` | GitHub OAuth entry point | No |
| `/auth/callback` | Receives session after OAuth, redirects to dashboard | No |
| `/dashboard` | Profile count, recent additions, basic metrics | Yes |
| `/profiles` | Paginated list with filter controls | Yes |
| `/profiles/:id` | Single profile detail view | Yes |
| `/search` | Natural language search input and results | Yes |
| `/account` | Current user info, role display | Yes |

---

## CSRF Protection

Every `POST`, `PUT`, or `DELETE` request from the web portal includes:

```
X-CSRF-Token: <value read from csrf_token cookie>
```

The backend compares this header against the `csrf_token` cookie value. A cross-origin malicious page can trigger a form submission with the cookie but cannot read the cookie value (blocked by Same-Origin Policy), so it cannot set the correct header. The request is rejected with `403 CSRF validation failed`.

---

## Environment Variables

```env
BACKEND_URL=https://your-backend.railway.app
PORT=3000
NODE_ENV=production
```

---

## Running Locally

```bash
npm install
cp .env.example .env
# edit .env — set BACKEND_URL to your local or deployed backend

npm start
# or for development with auto-reload:
npm run dev
```

The web portal expects the backend to be running. Start the backend first.

---

## Deploying to Railway

```bash
railway login
railway init
railway up
```

Set environment variables in the Railway dashboard. Make sure `BACKEND_URL` points to the deployed backend, and that the backend's `FRONTEND_URL` and `GITHUB_REDIRECT_URI` both point back to this portal's URL.

---

## Engineering Standards

**Commit format:** `type(scope): message`
```
feat(auth): implement github oauth cookie flow
feat(dashboard): add profile metrics overview
fix(csrf): attach csrf token header on all mutations
```

**Branch naming:** `feat/`, `fix/`, `chore/`

**PRs:** All changes merged via PR. CI must pass.

**CI (GitHub Actions on PR to main):**
- ESLint
- Build check
- Dependency audit
