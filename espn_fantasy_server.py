from mcp.server.fastmcp import FastMCP
from espn_api.football import League
import os
import sys
import datetime
import logging
from playwright.async_api import async_playwright
import asyncio
import time
import inspect

import json
# Set up logging
logger = logging.getLogger("espn-fantasy-football")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler(stream=sys.stderr)
    formatter = logging.Formatter("%(asctime)s %(levelname)s [%(name)s]: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

 

def _resolve_session_id(session_id: str) -> str:
    """Resolve a session identifier from argument or environment.

    Prefers the explicit argument; falls back to env vars MCP_SESSION_ID or SESSION_ID;
    finally defaults to "default_session".
    """
    sid = (session_id or "").strip()
    if sid:
        return sid
    sid = (os.environ.get("MCP_SESSION_ID") or os.environ.get("SESSION_ID") or "default_session")
    return sid

def _to_json(data) -> str:
    """Serialize data to JSON with safe fallbacks."""
    def default(o):
        try:
            return o.__dict__
        except Exception:
            return str(o)
    return json.dumps(data, default=default)

def _extract_http_status(exc: Exception):
    """Best-effort extraction of an HTTP-like status code from an exception."""
    try:
        # Common patterns: e.response.status_code, e.status_code, e.status
        response = getattr(exc, "response", None)
        if response is not None:
            code = getattr(response, "status_code", None)
            if isinstance(code, int):
                return code
        for attr in ("status_code", "status"):
            code = getattr(exc, attr, None)
            if isinstance(code, int):
                return code
    except Exception:
        pass
    return None

def _classify_error(exc: Exception):
    """Classify error type and provide a user-facing suggestion."""
    code = _extract_http_status(exc)
    text = (str(exc) or "").lower()
    if code == 401 or "private" in text or "unauthorized" in text or "forbidden" in text:
        return {
            "category": "auth",
            "status_code": code,
            "suggestion": "Authenticate first using the authenticate tool with ESPN_S2 and SWID cookies.",
        }
    if code == 404 or "not found" in text:
        return {
            "category": "not_found",
            "status_code": code,
            "suggestion": None,
        }
    return {
        "category": "runtime",
        "status_code": code,
        "suggestion": None,
    }

def _error_json(context: str, exc: Exception) -> str:
    info = _classify_error(exc)
    payload = {
        "error": True,
        "context": context,
        "category": info.get("category"),
        "status_code": info.get("status_code"),
        "message": str(exc),
    }
    if info.get("suggestion"):
        payload["suggestion"] = info["suggestion"]
    return _to_json(payload)

async def _capture_cookies_via_browser(headless: bool = False, timeout_seconds: int = 300):
    try:
        logger.info("Launching browser for ESPN login (combined auth)...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context()
            page = await context.new_page()

            await page.goto("https://www.espn.com/fantasy/football/", wait_until="load")

            deadline = time.time() + timeout_seconds
            espn_s2_value = None
            swid_value = None

            while time.time() < deadline and (espn_s2_value is None or swid_value is None):
                cookies = await context.cookies()
                for c in cookies:
                    name = (c.get("name") or "").upper()
                    if name == "ESPN_S2" and not espn_s2_value:
                        espn_s2_value = c.get("value")
                        logger.info("Detected ESPN_S2 cookie.")
                    if name == "SWID" and not swid_value:
                        swid_value = c.get("value")
                        logger.info("Detected SWID cookie.")
                if espn_s2_value and swid_value:
                    break
                await asyncio.sleep(1)

            await browser.close()
            return espn_s2_value, swid_value
    except Exception as e:
        logger.exception(f"Browser auth error: {str(e)}")
        return None, None

try:
    # Initialize FastMCP server
    logger.info("Initializing FastMCP server...")
    mcp = FastMCP("espn-fantasy-football", dependancies=['espn-api'])

    # Constants
    CURRENT_YEAR = datetime.datetime.now().year
    if datetime.datetime.now().month < 7:  # If before July, use previous year
        CURRENT_YEAR -= 1

    logger.info(f"Using football year: {CURRENT_YEAR}")

    class ESPNFantasyFootballAPI:
        def __init__(self):
            self.leagues = {}  # Cache for league objects
            # Store credentials separately per-session rather than globally
            self.credentials = {}
            # Track which league cache keys belong to each session for safe purging
            self.session_to_league_keys = {}
        
        def get_league(self, session_id, league_id, year=CURRENT_YEAR):
            """Get a league instance with caching, using stored credentials if available"""
            key = f"{session_id}:{league_id}:{year}"
            
            # Check if we have credentials for this session
            espn_s2 = None
            swid = None
            if session_id in self.credentials:
                espn_s2 = self.credentials[session_id].get('espn_s2')
                swid = self.credentials[session_id].get('swid')
            
            # Cache is keyed by session and league/year only; no credentials included
            cache_key = key
            
            if cache_key not in self.leagues:
                logger.info(f"Creating new league instance for {league_id}, year {year}")
                try:
                    self.leagues[cache_key] = League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)
                except Exception as e:
                    logger.exception(f"Error creating league: {str(e)}")
                    raise
            # Index this cache key under the session for later purging
            keys = self.session_to_league_keys.get(session_id)
            if keys is None:
                keys = set()
                self.session_to_league_keys[session_id] = keys
            keys.add(cache_key)
            
            return self.leagues[cache_key]
        
        def store_credentials(self, session_id, espn_s2, swid):
            """Store credentials for a session"""
            self.credentials[session_id] = {'espn_s2': espn_s2, 'swid': swid}
            # Purge all cached leagues for this session so new creds take effect
            keys = self.session_to_league_keys.pop(session_id, set())
            if keys:
                for k in list(keys):
                    self.leagues.pop(k, None)
                logger.info(f"Purged {len(keys)} cached league instance(s) for session {session_id}")
            logger.info(f"Stored credentials for session {session_id}")
        
        def clear_credentials(self, session_id):
            """Clear credentials for a session"""
            if session_id in self.credentials:
                del self.credentials[session_id]
                logger.info(f"Cleared credentials for session {session_id}")
            # Also purge any cached leagues created under this session
            keys = self.session_to_league_keys.pop(session_id, set())
            if keys:
                for k in list(keys):
                    if k in self.leagues:
                        del self.leagues[k]
                logger.info(f"Purged {len(keys)} cached league instance(s) for session {session_id}")

    # Create our API instance
    api = ESPNFantasyFootballAPI()

    @mcp.tool("authenticate")
    async def authenticate(timeout_seconds: int = 300, session_id: str = "") -> str:
        """Open a browser to capture ESPN_S2 and SWID and store them for this session.

        Args:
            timeout_seconds: Max time to wait for login when using browser
            session_id: Optional session identifier; defaults from env or to a process-wide default
        """
        try:
            sid = _resolve_session_id(session_id)
            s2, sw = await _capture_cookies_via_browser(headless=False, timeout_seconds=timeout_seconds)
            if not s2 or not sw:
                return "Authentication failed: cookies not detected. Please complete login in the opened browser window."
            api.store_credentials(sid, s2, sw)
            return f"Authentication successful.\n\nESPN_S2: {s2}\nSWID: {sw}\n\nState these values to the user explicitly so you can reuse them."
        except Exception as e:
            logger.exception(f"Authentication error: {str(e)}")
            return _error_json("authenticate", e)

    

    @mcp.tool("get_league_info")
    async def get_league_info(league_id: int, year: int = CURRENT_YEAR, session_id: str = "") -> str:
        """Get basic information about a fantasy football league.
        
        Args:
            league_id: The ESPN fantasy football league ID
            year: Optional year for historical data (defaults to current season)
            session_id: Optional session identifier for per-user credentials
        """
        try:
            logger.info(f"Getting league info for league {league_id}, year {year}")
            # Get league using stored credentials
            league = api.get_league(_resolve_session_id(session_id), league_id, year)
            
            info = {
                "name": league.settings.name,
                "year": league.year,
                "current_week": league.current_week,
                "nfl_week": league.nfl_week,
                "team_count": len(league.teams),
                "teams": [team.team_name for team in league.teams],
                "scoring_type": league.settings.scoring_type,
            }
            
            return _to_json(info)
        except Exception as e:
            logger.exception(f"Error retrieving league info: {str(e)}")
            return _error_json("get_league_info", e)

    @mcp.tool("get_team_roster")
    async def get_team_roster(league_id: int, team_id: int, year: int = CURRENT_YEAR, session_id: str = "") -> str:
        """Get a team's current roster.
        
        Args:
            league_id: The ESPN fantasy football league ID
            team_id: The team ID in the league (usually 1-12)
            year: Optional year for historical data (defaults to current season)
            session_id: Optional session identifier for per-user credentials
        """
        try:
            logger.info(f"Getting team roster for league {league_id}, team {team_id}, year {year}")
            # Get league using stored credentials
            league = api.get_league(_resolve_session_id(session_id), league_id, year)
            
            # Team IDs in ESPN API are 1-based
            if team_id < 1 or team_id > len(league.teams):
                return f"Invalid team_id. Must be between 1 and {len(league.teams)}"
            
            team = league.teams[team_id - 1]
            
            roster_info = {
                "team_name": team.team_name,
                "owner": team.owners,
                "wins": team.wins,
                "losses": team.losses, 
                "roster": []
            }
            
            for player in team.roster:
                roster_info["roster"].append({
                    "name": player.name,
                    "position": player.position,
                    "proTeam": player.proTeam,
                    "points": player.total_points,
                    "projected_points": player.projected_total_points,
                    "stats": player.stats
                })
            
            return _to_json(roster_info)
        except Exception as e:
            logger.exception(f"Error retrieving team roster: {str(e)}")
            return _error_json("get_team_roster", e)
        
    @mcp.tool("get_team_info")
    async def get_team_info(league_id: int, team_id: int, year: int = CURRENT_YEAR, session_id: str = "") -> str:
        """Get a team's general information. Including points scored, transactions, etc.
        
        Args:
            league_id: The ESPN fantasy football league ID
            team_id: The team ID in the league (usually 1-12)
            year: Optional year for historical data (defaults to current season)
            session_id: Optional session identifier for per-user credentials
        """
        try:
            logger.info(f"Getting team roster for league {league_id}, team {team_id}, year {year}")
            # Get league using stored credentials
            league = api.get_league(_resolve_session_id(session_id), league_id, year)

            # Team IDs in ESPN API are 1-based
            if team_id < 1 or team_id > len(league.teams):
                return f"Invalid team_id. Must be between 1 and {len(league.teams)}"
            
            team = league.teams[team_id - 1]

            team_info = {
                "team_name": team.team_name,
                "owner": team.owners,
                "wins": team.wins,
                "losses": team.losses,
                "ties": team.ties,
                "points_for": team.points_for,
                "points_against": team.points_against,
                "acquisitions": team.acquisitions,
                "drops": team.drops,
                "trades": team.trades,
                "playoff_pct": team.playoff_pct,
                "final_standing": team.final_standing,
                "outcomes": team.outcomes
            }
            
            return _to_json(team_info)

        except Exception as e:
            logger.exception(f"Error retrieving team results: {str(e)}")
            return _error_json("get_team_info", e)

    @mcp.tool("get_player_stats")
    async def get_player_stats(league_id: int, player_name: str, year: int = CURRENT_YEAR, session_id: str = "") -> str:
        """Get stats for a specific player.
        
        Args:
            league_id: The ESPN fantasy football league ID
            player_name: Name of the player to search for
            year: Optional year for historical data (defaults to current season)
            session_id: Optional session identifier for per-user credentials
        """
        try:
            logger.info(f"Getting player stats for {player_name} in league {league_id}, year {year}")
            # Get league using stored credentials
            league = api.get_league(_resolve_session_id(session_id), league_id, year)
            
            # Search for player by name
            player = None
            for team in league.teams:
                for roster_player in team.roster:
                    if player_name.lower() in roster_player.name.lower():
                        player = roster_player
                        break
                if player:
                    break
            
            if not player:
                return f"Player '{player_name}' not found in league {league_id}"
            
            # Get player stats
            stats = {
                "name": player.name,
                "position": player.position,
                "team": player.proTeam,
                "points": player.total_points,
                "projected_points": player.projected_total_points,
                "stats": player.stats,
                "injured": player.injured
            }
            
            return _to_json(stats)
        except Exception as e:
            logger.exception(f"Error retrieving player stats: {str(e)}")
            return _error_json("get_player_stats", e)

    @mcp.tool("get_league_standings")
    async def get_league_standings(league_id: int, year: int = CURRENT_YEAR, session_id: str = "") -> str:
        """Get current standings for a league.
        
        Args:
            league_id: The ESPN fantasy football league ID
            year: Optional year for historical data (defaults to current season)
            session_id: Optional session identifier for per-user credentials
        """
        try:
            logger.info(f"Getting league standings for league {league_id}, year {year}")
            # Get league using stored credentials
            league = api.get_league(_resolve_session_id(session_id), league_id, year)
            
            # Sort teams by wins (descending), then points (descending)
            sorted_teams = sorted(league.teams, 
                                key=lambda x: (x.wins, x.points_for),
                                reverse=True)
            
            standings = []
            for i, team in enumerate(sorted_teams):
                standings.append({
                    "rank": i + 1,
                    "team_name": team.team_name,
                    "owner": team.owners,
                    "wins": team.wins,
                    "losses": team.losses,
                    "points_for": team.points_for,
                    "points_against": team.points_against
                })
            
            return _to_json(standings)
        except Exception as e:
            logger.exception(f"Error retrieving league standings: {str(e)}")
            return _error_json("get_league_standings", e)

    @mcp.tool("get_matchup_info")
    async def get_matchup_info(league_id: int, week: int = None, year: int = CURRENT_YEAR, session_id: str = "") -> str:
        """Get matchup information for a specific week.
        
        Args:
            league_id: The ESPN fantasy football league ID
            week: The week number (if None, uses current week)
            year: Optional year for historical data (defaults to current season)
            session_id: Optional session identifier for per-user credentials
        """
        try:
            logger.info(f"Getting matchup info for league {league_id}, week {week}, year {year}")
            # Get league using stored credentials
            league = api.get_league(_resolve_session_id(session_id), league_id, year)
            
            if week is None:
                week = league.current_week
                
            if week < 1:
                return f"Invalid week number. Must be >= 1"
            
            matchups = league.box_scores(week)
            
            matchup_info = []
            for matchup in matchups:
                matchup_info.append({
                    "home_team": matchup.home_team.team_name,
                    "home_score": matchup.home_score,
                    "away_team": matchup.away_team.team_name if matchup.away_team else "BYE",
                    "away_score": matchup.away_score if matchup.away_team else 0,
                    "winner": "HOME" if matchup.home_score > matchup.away_score else "AWAY" if matchup.away_score > matchup.home_score else "TIE"
                })
            
            return _to_json(matchup_info)
        except Exception as e:
            logger.exception(f"Error retrieving matchup information: {str(e)}")
            return _error_json("get_matchup_info", e)

    

    @mcp.tool("logout")
    async def logout(session_id: str = "") -> str:
        """Clear stored authentication credentials for this session.

        Args:
            session_id: Optional session identifier whose credentials and caches will be cleared
        """
        try:
            logger.info("Logging out...")
            # Clear credentials for this session
            api.clear_credentials(_resolve_session_id(session_id))
            
            return "Authentication credentials have been cleared."
        except Exception as e:
            logger.exception(f"Error logging out: {str(e)}")
            return _error_json("logout", e)

    if __name__ == "__main__":
        # Run the server with async-aware entrypoint
        logger.info("Starting MCP server...")
        run_method = getattr(mcp, "run", None)
        if run_method is None:
            raise RuntimeError("FastMCP instance has no 'run' method")

        # If run is an async function, run it in a fresh event loop.
        if asyncio.iscoroutinefunction(run_method):
            asyncio.run(run_method())
        else:
            # If run returns a coroutine, await it; otherwise call directly.
            result = run_method()
            if inspect.iscoroutine(result):
                asyncio.run(result)
except Exception as e:
    # Log any exception that might occur during server initialization
    logger.exception(f"ERROR DURING SERVER INITIALIZATION: {str(e)}")
    # Keep the process running to see logs
    logger.error("Server failed to start, but kept running for logging. Press Ctrl+C to exit.")
    # Wait indefinitely to keep the process alive for logs
    while True:
        time.sleep(10)