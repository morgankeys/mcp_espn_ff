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
  - In-memory session (set by tools like browser auth)
- **Loading**:
  - Always load `.env` if present (via `python-dotenv`)
  - Read process env after `.env` so process env can override
- **Validation**:
  - At startup, compute an “auth status” (both cookies present vs missing)
  - Tools can query this status and receive clear guidance

### Persistence strategy (by mode)
- **Mode 1 – Launch from AI client**
  - Treat process env as read-only (cannot persist to connector-managed env from the server)
  - On browser auth:
    - Set `os.environ` for current process (works for current run)
    - Return the cookie values (or masked with a “reveal” flag) so the user can update the connector’s env UI
- **Mode 2 – Launch independently**
  - Load `.env` on startup
  - On browser auth:
    - Write/overwrite `ESPN_S2` and `SWID` in `.env`
    - Refresh in-memory env and cache, so subsequent tools work immediately

### Mode detection
- Preferred: explicit CLI flag `--mode client|independent`
- Fallback auto-detect:
  - If `.env` exists → default to `independent`
  - Else if special marker env var (e.g., `MCP_LAUNCHED=1`) is present → `client`
- Allow override via CLI/env if auto-detect is wrong

### Startup flow
1) Parse CLI flags/env to determine mode.
2) Load `.env` if present.
3) Read `ESPN_S2`/`SWID` from env; set an `AuthState` object.
4) Initialize services:
   - `CredentialManager` (abstraction over env, `.env`, in-memory)
   - `LeagueService` (wraps `espn_api.football.League` with caching)
5) Register tools; expose a “status” tool to show auth state and next steps.

### Tools (API surface)
- `auth_status()`:
  - Returns whether credentials are available and where they were sourced from
  - Provides next-step hints (set env in connector UI; run browser auth; create `.env`)
- `authenticate_browser(headless: bool = False, persist: bool = True, reveal: bool = False)`:
  - Opens Playwright, waits for cookies
  - In client mode:
    - Sets `os.environ` for this process
    - If `persist=True`, returns values (masked unless `reveal=True`) with copy/paste instructions for connector env UI
  - In independent mode:
    - Writes/updates `.env` (if `persist=True`)
    - Reloads env for current run
- `use_env_credentials()`:
  - Loads `ESPN_S2`/`SWID` from current env into the session cache (idempotent)
- `set_credentials(espn_s2: str, swid: str, persist: bool = False)`:
  - Always sets in-memory session + process env
  - If independent mode and `persist=True`, writes to `.env`
- `logout(clear_env: bool = False)`:
  - Clears in-memory/session credentials and cache
  - If `clear_env=True` in independent mode, removes keys from `.env` and current process env
- Existing ESPN tools (`get_league_info`, `get_team_roster`, etc.):
  - Depend only on `LeagueService.get_league(...)` which uses `CredentialManager` for credentials and a cache keyed by `(league_id, year, session_id)`

### Services and caching
- `CredentialManager`
  - `get()` returns best available credentials (session > process env > `.env`)
  - `set(espn_s2, swid, persist_mode)` applies to memory, process env, and optionally `.env`
  - `clear()` clears memory; optional `.env` pruning
- `LeagueService`
  - `get_league(session_id, league_id, year)` builds a strong cache key
  - Creates league with current creds; refreshes object if creds change or on 401
  - Small TTL or invalidation on `set_credentials` to avoid stale auth

### File layout
- `server.py` (entrypoint, CLI, tool registry)
- `config.py` (mode detection, dotenv loading, constants)
- `auth.py` (`CredentialManager`, `.env` writer, masking helpers)
- `services/espn.py` (`LeagueService`, ESPN API interactions)
- `tools/`:
  - `auth_tools.py` (`authenticate_browser`, `auth_status`, `set_credentials`, `logout`, `use_env_credentials`)
  - `league_tools.py` (league/team/player queries)
- `.env` (ignored by VCS; sample `.env.example` in repo)
- Add `python-dotenv` to `pyproject.toml`

### Error handling and UX
- Consistent, friendly messages with actionable next steps per mode
- Mask secrets by default; `reveal=True` only when user requests
- Detect private-league/401 errors and recommend auth flows
- Logs to stderr; never log secret values

### Security
- Mask outputs unless explicitly requested
- Don’t write `.env` unless in independent mode or a user passes `persist=True`
- Provide a config flag to disable any persistence entirely

### Implementation steps
- Add `python-dotenv` and the new modules
- Implement `CredentialManager` and `.env` writer/reader
- Implement `LeagueService` with cache and 401-refresh behavior
- Refactor tools to call through these services
- Add CLI (`--mode`, `--headless`, `--no-persist`)
- Add `auth_status` first to validate the config paths
- Write `.env.example` and README snippets for both modes


# To do list

# To do list
1) Dependencies and scaffolding
- [ ] Add `python-dotenv`: `uv add python-dotenv`
- [ ] Create `.env.example` with `ESPN_S2` and `SWID`; ensure `.env` is git-ignored
- [ ] Create files/dirs: `server.py`, `config.py`, `auth.py`, `services/espn.py`, `tools/auth_tools.py`, `tools/league_tools.py`

2) Mode detection and config
- [ ] Implement `config.py` with `detect_mode(...)`, `load_dotenv_if_present()`, and a settings dataclass
- [ ] Add CLI flags in entrypoint: `--mode`, `--headless`, `--no-persist`; print selected mode on startup

3) CredentialManager
- [ ] Implement `get()`, `set(espn_s2, swid, persist=False)`, `clear()`, `source()` and masking helpers
- [ ] Implement `.env` write/update/remove for independent mode
- [ ] Basic unit tests for get/set/clear precedence

4) LeagueService
- [ ] Implement `get_league(session_id, league_id, year)` with cache key `(session_id, league_id, year)`
- [ ] Resolve credentials via `CredentialManager`; create/cached `League`
- [ ] Invalidate/refresh on credential change or 401 errors

5) Auth tools
- [ ] `auth_status()`
- [ ] `authenticate_browser(headless=False, persist=True, reveal=False)` (returns cookies for copy/paste in client mode; writes `.env` in independent mode when `persist=True`)
- [ ] `use_env_credentials()`
- [ ] `set_credentials(espn_s2, swid, persist=False)`
- [ ] `logout(clear_env=False)`

6) ESPN tools refactor
- [ ] Update: `get_league_info`, `get_team_roster`, `get_team_info`, `get_player_stats`, `get_league_standings`, `get_matchup_info` to use `LeagueService`
- [ ] Normalize error handling (401/private league guidance)
- [ ] Fix any existing cache key bugs during refactor

7) Docs and examples
- [ ] Update `README.md` with instructions for client mode and independent mode
- [ ] Add example commands and connector UI guidance; include security notes about secrets

8) QA
- [ ] Manual test matrix: client mode with env, independent mode with `.env`, browser auth with `persist=True/False`
- [ ] Verify secrets are masked in outputs and never logged