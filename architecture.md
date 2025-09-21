# Architecture goals
The following are guidelines for how the server should work.

## Launch contexts
The server can be started in different contexts; behavior is inferred from available credentials:

### Process env–backed (AI client/chat app)
In this context, the AI client/chat app calls a command to start the server on demand.
- Credentials will be stored as environment variables in the connector configuration

### .env–backed (independent)
In this context, the server is manually started by the user and the AI client/chat app is configured to connect to the already running server.
- Credentials will be stored in an .env file that is colocated with the server.

The server should be able to gracefully check for environment variables and, if no variables are found, alert the user.

There should also be a tool that will open a browser and allow the user to sign in. Once the user has signed in, the server should automatically grab the correct cookie credentials and save them as the appropriate environment variables.

# Architecture plan
Design a small, modular server that supports both launch contexts with explicit, safe handling of credentials and clear fallbacks. Separate configuration/credentials, ESPN access, and tool endpoints.

### Configuration and credentials
- **Credential names**: `ESPN_S2`, `SWID`
- **Sources (precedence)**:
  - Process env (from connector UI or shell)
  - `.env` file (local dev/independent context)

- **Loading**:
  - Always load `.env` if present (via `python-dotenv`)
  - Read process env after `.env` so process env can override
  - If both are present, warn the user that the process environment will override (and how to change this)
  - If neither is present or values are empty/invalid, tools automatically trigger browser authentication; no manual check required

- **Validation**:
  - At startup, compute an internal "auth status" (both cookies present vs missing)
  - `AuthState` fields:
    - `source`: one of `process_env`, `dot_env`, `none`
    - `is_valid`: boolean, based on non-empty values (and/or a validation probe on first use)
    - `last_checked`: timestamp of last validation
    - `masked`: mapping with masked `ESPN_S2` and `SWID` for diagnostics
  - Used by `ensure_authenticated(...)` to decide whether to trigger browser auth; not user-facing

### Persistence strategy (by source)
- Credential source is implicitly determined at runtime based on where valid credentials are found:
  - If valid `ESPN_S2` and `SWID` exist in the process environment → process env–backed run (typically AI client)
  - Else if valid values exist in `.env` → `.env`–backed run (typically independent)
  - Else → no credentials available; prompt the user to authenticate.
- **Process env–backed run (typically launched by AI client)**
  - Treat process env as read-only (cannot persist to connector-managed env from the server)
  - If env vars are present but empty or invalid:
    - Prompt the user to run browser authentication
    - Set `os.environ` for the current process (works for this run)
    - Return cookie values in the tool response so the user can update the connector’s env UI
  - On browser auth:
    - Set `os.environ` for current process (works for current run)
    - Return the cookie values so the user can update the connector’s env UI
- **`.env`–backed run (typically independent launch)**
  - Load `.env` on startup
  - If neither source has credentials, warn the user that they will need to authenticate (e.g., via the browser auth tool)
  - On browser auth:
    - Print `ESPN_S2` and `SWID` in chat so that user can update the connector or local `.env`
    - Add `ESPN_S2` and `SWID` to os.environ so that tool calls will work immediately.
    - Warn user that they should delete chat to hide secrets

### Source detection
- The credential source is inferred from available valid credentials:
  - If valid `ESPN_S2` and `SWID` exist in the process environment → process env–backed
  - Else if valid values exist in `.env` → `.env`–backed
  - Else → no credentials; prompt the user to authenticate
  - If process env vars exist but are empty/invalid → treat as process env–backed with invalid creds; prompt browser auth and instruct updating the connector’s env

### Startup flow
1) Load `.env` if present.
2) Infer credentials source implicitly:
   - If valid `ESPN_S2`/`SWID` in process env → process env–backed run
   - Else if valid values in `.env` → `.env`–backed run
   - Else → unauthenticated; prompt for browser auth
3) Set an `AuthState` object based on the detected source.
4) Initialize services:
   - `CredentialManager` (abstraction over env, `.env`, in-memory)
   - `LeagueService` (wraps `espn_api.football.League` with caching)
5) Register tools.

### Playwright lifecycle
- Single-flight: Only one browser authentication can run at a time. Concurrent requests receive “Authentication is already in progress. Please wait for the current login to complete.”
- Timeout: `authenticate(timeout_seconds=180)` waits up to the provided seconds for cookies before cancelling gracefully with guidance to retry or increase the timeout.
- Cleanup: Browser context and browser are always closed in finally blocks, and also on cancellation, to avoid orphaned processes.

### Tools (API surface)
- `authenticate_browser()`:
  - Opens Playwright, waits for cookies
- Central helper (internal): `ensure_authenticated()`
  - Checks for valid credentials from process env/`.env`
  - If missing or invalid, launches the browser auth flow (same logic as `authenticate_browser`)
- Existing ESPN tools (`get_league_info`, `get_team_roster`, etc.):
  - Depend only on `LeagueService.get_league(...)` which uses `CredentialManager` for credentials and a cache keyed by `(league_id, year)`
  - Each tool calls `ensure_authenticated(...)` up-front so the user never has to manually check auth

### Services and caching
- `CredentialManager`
  - `get()` returns best available credentials (process env > `.env`)
  - `set(espn_s2, swid, persist_mode)` applies to memory, process env, and optionally `.env`
- `LeagueService`
  - `get_league(league_id, year)` builds a strong cache key
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

### 401 retry policy
- Trigger: A tool call encounters an authentication error (HTTP 401) or a "Private league" error from the ESPN API.
- Step 1: Attempt re-authentication once via `ensure_authenticated(...)` (uses single-flight lock so only one auth runs at a time).
- Step 2: Refresh in-memory credentials and invalidate any cached league instance tied to old credentials.
- Step 3: Retry the original operation exactly once with the fresh credentials.
- Step 4: If the retry still fails with 401/private, return an actionable message instructing the user to run `authenticate` and update the connector/.env with the displayed cookies. Do not loop.
- Logging: Record the error and outcome to stderr without leaking secret values.

### Security
- Mask outputs unless explicitly requested


### Implementation steps
- Add `python-dotenv` and the new modules
- Implement `CredentialManager` and `.env` writer/reader in `auth.py`
- Implement `authenticate_browser(headless=False, persist=True, reveal=False)` and internal `ensure_authenticated(headless=False, persist=True)`
- Implement `LeagueService` with cache and 401-refresh behavior in `espn_service.py`
- Implement tool endpoints in `tools.py` that call `ensure_authenticated` and delegate to `LeagueService`
- Write `.env.example` and README snippets explaining implicit credential sourcing and the browser auth flow
