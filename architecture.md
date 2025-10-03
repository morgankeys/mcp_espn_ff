# Architecture goals
The following are guidelines for how the server should work.

# Architecture plan
Design a small, modular server that seamlessly handles authentication. 

## Authentication
There should also be a method that will open a browser and allow the user to sign in. Once the user has signed in, the server should automatically grab the correct cookie credentials and save them to a database.
- **ESPN Credential names**: `espn_s2`, `SWID`

### Credential database
The server should use a simple SQLite database to securely store credentials and secrets. In this way, the server should be able to store credentials for multiple leagues or accounts.

Credentials table:
- SWID (primary key)
- espn_s2

Leagues table:
- league_id (primary key)
- team_id
- team_name
- SWID (foreign key -> credentials table)

### Authentication
The service should also allow users to sign in to their espn fantasy football account via playwrite browser and then retrieve the appropriate credentials.

The folowing is an outline of how authentication should work:

- Open playwrite browser to https://www.espn.com/fantasy/football/, poll for cookie with credentials
- Save SWID, espn_s2. Create row in credentials table with these values.
- Make sure the browser is still on https://www.espn.com/fantasy/football/
- Find element id="fantasy-feed-items"
- Within that element, find every <a> tag with class favItem__team. For each <a>:
  - find the href
  - parse out leagueId=<int>, save as league_id 
  - parse out teamId=2, save as team_id
  - Find div class=”favItem__name” and save the string as team_name
  - Save league_id, team_id, team_name, SWID to leagues table

### Playwright lifecycle
- Single-flight: Only one browser authentication can run at a time. Concurrent requests receive “Authentication is already in progress. Please wait for the current login to complete.”
- Timeout: `authenticate(timeout_seconds=180)` waits up to the provided seconds for cookies before cancelling gracefully with guidance to retry or increase the timeout.
- Cleanup: Browser context and browser are always closed in finally blocks, and also on cancellation, to avoid orphaned processes.

### 401 retry policy
- Trigger: A tool call encounters an authentication error (HTTP 401) or a "Private league" error from the ESPN API.
- Step 1: Attempt re-authentication once via `ensure_authenticated(...)` (uses single-flight lock so only one auth runs at a time).
- Step 2: Refresh in-memory credentials and invalidate any cached league instance tied to old credentials.
- Step 3: Retry the original operation exactly once with the fresh credentials.
- Step 4: If the retry still fails with 401/private, return an actionable message instructing the user to run `authenticate` and update the connector/.env with the displayed cookies. Do not loop.
- Logging: Record the error and outcome to stderr without leaking secret values.

### Security
- Mask outputs unless explicitly requested

## Tools (API surface)
- Get leauges
- Existing ESPN tools (`get_league_info`, `get_team_roster`, etc.):
  - Depend only on `LeagueService.get_league(...)` which uses `CredentialManager` for credentials and a cache keyed by `(league_id, year)`
  - Each tool calls `ensure_authenticated(...)` up-front so the user never has to manually check auth

## Services and caching
- `CredentialManager`
  - `get()` returns best available credentials
  - `set(espn_s2, swid)`
- `LeagueService`
  - `get_league(league_id, year)` builds a strong cache key
  - Creates league with current creds; refreshes object if creds change or on 401
  - Small TTL or invalidation on `set_credentials` to avoid stale auth
- `authenticate_browser()`:
  - Opens Playwright, waits for cookies
- Central helper (internal): `ensure_authenticated()`
  - Checks for valid credentials from process env/`.env`
  - If missing or invalid, launches the browser auth flow (same logic as `authenticate_browser`)

## File layout
- `server.py` (entrypoint, tool registry)
- `auth.py` (tbd)
- `espn_service.py` (`LeagueService`, ESPN API interactions)
- `tools.py` (all tool endpoints; each calls `ensure_authenticated` internally)
- `.env` (ignored by VCS; sample `.env.example` in repo)
- Add `python-dotenv` to `pyproject.toml`

## Error handling and UX
- Consistent, friendly messages with actionable next steps
- Detect private-league/401 errors and auto-trigger `ensure_authenticated(...)` once; if it still fails, surface guidance
- Logs to stderr; never log secret values