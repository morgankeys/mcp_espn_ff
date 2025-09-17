# Architecture goals
The following are guidelines for how the server should work.

## Modes of usage
The server should have two modes by which it is started and operates:

### 1. Launch from AI client/chat app
In this mode, the AI client/chat app calls a command to start the server on demand.
- Credentials will be stored as environment variables in the connector configuraiont

### 2. Launch independently
In independent mode, the server is manually started by the user and the AI client/chat app is configured to connect to the already running server.
- Credentials will be stored in an .env file that is colocated with the server.

The server should be able to gracefully check for environment variables and, if no variables are found, alert the user.

There should also be a tool that will open a browser and allow the user to sign-in. Once the user has signed in, the server should automatically grab the correct cookie credentials and save them as the appropriate environment variables.

# Architecture plan
Design a small, modular server that supports both launch modes with explicit, safe handling of credentials and clear fallbacks. Separate configuration/credentials, ESPN access, and tool endpoints.

### Configuration and credentials
- **Credential names**: `ESPN_S2`, `SWID`
- **Sources (precedence)**:
  - Process env (from connector UI or shell)
  - `.env` file (local dev/independent mode)

- **Loading**:
  - Always load `.env` if present (via `python-dotenv`)
  - Read process env after `.env` so process env can override
  - If both are present, warn the user that the process environment will override (and how to change this)
  - If neither is present or values are empty/invalid, tools automatically trigger browser authentication; no manual check required

- **Validation**:
  - At startup, compute an internal “auth status” (both cookies present vs missing)
  - Used by `ensure_authenticated(...)` to decide whether to trigger browser auth; not user-facing

### Persistence strategy (by mode)
- Mode is implicitly determined at runtime based on where valid credentials are found:
  - If valid `ESPN_S2` and `SWID` exist in the process environment → use Mode 1 (AI client).
  - Else if valid values exist in `.env` → use Mode 2 (independent).
  - Else → no credentials available; prompt the user to authenticate.
- **Mode 1 – Launch from AI client**
  - Treat process env as read-only (cannot persist to connector-managed env from the server)
  - If env vars are present but empty or invalid:
    - Prompt the user to run browser authentication
    - Set `os.environ` for the current process (works for this run)
    - Return cookie values (masked unless `reveal=True`) so the user can update the connector’s env UI
  - On browser auth:
    - Set `os.environ` for current process (works for current run)
    - Return the cookie values (or masked with a “reveal” flag) so the user can update the connector’s env UI
- **Mode 2 – Launch independently**
  - Load `.env` on startup
  - On browser auth:
    - Write/overwrite `ESPN_S2` and `SWID` in `.env`
    - Refresh in-memory env and cache, so subsequent tools work immediately
  - If neither source has credentials, warn the user that they will need to authenticate (e.g., via the browser auth tool)

### Mode detection
- No explicit mode setting. Mode is inferred from credentials:
  - If valid `ESPN_S2` and `SWID` exist in the process environment → Mode 1 (AI client)
  - Else if valid values exist in `.env` → Mode 2 (independent)
  - Else → no credentials; prompt the user to authenticate
  - If process env vars exist but are empty/invalid → treat as Mode 1 with invalid creds; prompt browser auth and instruct updating the connector’s env

### Startup flow
1) Load `.env` if present.
2) Infer credentials source implicitly:
   - If valid `ESPN_S2`/`SWID` in process env → treat as AI client (Mode 1)
   - Else if valid values in `.env` → treat as independent (Mode 2)
   - Else → unauthenticated; prompt for browser auth
3) Set an `AuthState` object based on the detected source.
4) Initialize services:
   - `CredentialManager` (abstraction over env, `.env`, in-memory)
   - `LeagueService` (wraps `espn_api.football.League` with caching)
5) Register tools.

### Tools (API surface)
- `authenticate_browser(headless: bool = False, persist: bool = True, reveal: bool = False)`:
  - Opens Playwright, waits for cookies
- Central helper (internal): `ensure_authenticated(headless: bool = False, persist: bool = True)`
  - Checks for valid credentials from process env/`.env`
  - If missing or invalid, launches the browser auth flow (same logic as `authenticate_browser`)
  - Persists according to `persist` and updates the current process env
- Existing ESPN tools (`get_league_info`, `get_team_roster`, etc.):
  - Depend only on `LeagueService.get_league(...)` which uses `CredentialManager` for credentials and a cache keyed by `(league_id, year, session_id)`
  - Each tool calls `ensure_authenticated(...)` up-front so the user never has to manually check auth

### Services and caching
- `CredentialManager`
  - `get()` returns best available credentials (process env > `.env`)
  - `set(espn_s2, swid, persist_mode)` applies to memory, process env, and optionally `.env`
  - `clear()` clears memory; optional `.env` pruning
- `LeagueService`
  - `get_league(session_id, league_id, year)` builds a strong cache key
  - Creates league with current creds; refreshes object if creds change or on 401
  - Small TTL or invalidation on `set_credentials` to avoid stale auth

### File layout
- `server.py` (entrypoint, tool registry)
- `auth.py` (dotenv loading, `CredentialManager`, masking helpers, `ensure_authenticated`, browser auth)
- `espn_service.py` (`LeagueService`, ESPN API interactions)
- `tools.py` (all tool endpoints; each calls `ensure_authenticated` internally)
- `.env` (ignored by VCS; sample `.env.example` in repo)
- Add `python-dotenv` to `pyproject.toml`

### Error handling and UX
- Consistent, friendly messages with actionable next steps
- Mask secrets by default; `reveal=True` only when user requests
- Detect private-league/401 errors and auto-trigger `ensure_authenticated(...)` once; if it still fails, surface guidance
- Logs to stderr; never log secret values

### Security
- Mask outputs unless explicitly requested


### Implementation steps
- Add `python-dotenv` and the new modules
- Implement `CredentialManager` and `.env` writer/reader in `auth.py`
- Implement `authenticate_browser(headless=False, persist=True, reveal=False)` and internal `ensure_authenticated(headless=False, persist=True)`
- Implement `LeagueService` with cache and 401-refresh behavior in `espn_service.py`
- Implement tool endpoints in `tools.py` that call `ensure_authenticated` and delegate to `LeagueService`
- Write `.env.example` and README snippets explaining implicit credential sourcing and the browser auth flow


# To do list

# To do list
1) Dependencies and scaffolding
- [ ] Add `python-dotenv`: `uv add python-dotenv`
- [ ] Create `.env.example` with `ESPN_S2` and `SWID`; ensure `.env` is git-ignored
- [ ] Create files: `server.py`, `auth.py`, `espn_service.py`, `tools.py`

2) Auth
- [ ] Implement `CredentialManager` and `.env` read/write helper functions in `auth.py`
- [ ] Implement `authenticate_browser(headless=False, persist=True, reveal=False)`
- [ ] Implement internal `ensure_authenticated(headless=False, persist=True)`

3) LeagueService
- [ ] Implement `get_league(session_id, league_id, year)` with cache key `(session_id, league_id, year)`
- [ ] Resolve credentials via `CredentialManager`; create/cached `League`
- [ ] Invalidate/refresh on credential change or 401 errors

4) Tools
- [ ] Implement `get_league_info`, `get_team_roster`, `get_team_info`, `get_player_stats`, `get_league_standings`, `get_matchup_info` in `tools.py` calling `ensure_authenticated` and using `LeagueService`

5) Docs and examples
- [ ] Update `README.md` with instructions for implicit credential sourcing and browser auth
- [ ] Add example commands and connector UI guidance; include security notes about secrets

6) QA
- [ ] Manual test matrix: process env present, `.env` present, and unauthenticated → browser auth triggers
- [ ] Verify secrets are masked in outputs and never logged