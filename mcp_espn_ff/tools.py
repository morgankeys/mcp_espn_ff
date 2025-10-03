import sys
import datetime
from mcp.server.fastmcp import FastMCP
from .espn_service import LeagueService, ensure_authenticated


def log_error(message: str) -> None:
    print(message, file=sys.stderr)


CURRENT_YEAR = datetime.datetime.now().year
if datetime.datetime.now().month < 7:
    CURRENT_YEAR -= 1


def create_tools(mcp: FastMCP) -> None:
    league_service = LeagueService()

    @mcp.tool(name="authenticate", description="Only needed if credentials are not present or not valid in process environment.")
    async def authenticate() -> str:
        try:
            espn_s2, swid, state = await ensure_authenticated()
            return (
                "Authentication successful.\n"
                f"ESPN_S2={espn_s2}\n"
                f"SWID={swid}\n"
                "These values are applied to this session. Copy them into your connector's env or a local .env."
            )
        except Exception as e:
            log_error(f"Authentication error: {str(e)}")
            return f"Authentication error: {str(e)}"

    @mcp.tool()
    async def get_league_info(league_id: int, year: int = CURRENT_YEAR) -> str:
        try:
            league = await league_service.get_league(league_id, year)
            info = {
                "name": league.settings.name,
                "year": league.year,
                "current_week": league.current_week,
                "nfl_week": league.nfl_week,
                "team_count": len(league.teams),
                "teams": [team.team_name for team in league.teams],
                "scoring_type": league.settings.scoring_type,
            }
            return str(info)
        except Exception as e:
            log_error(f"Error retrieving league info: {str(e)}")
            if "401" in str(e) or "Private" in str(e):
                return (
                    "This appears to be a private league. Run the authenticate tool to login via browser.\n"
                    "After login, credentials (ESPN_S2 and SWID) will be displayed so you can update your connector env or .env."
                )
            return f"Error retrieving league: {str(e)}"

    @mcp.tool()
    async def get_team_roster(league_id: int, team_id: int, year: int = CURRENT_YEAR) -> str:
        try:
            league = await league_service.get_league(league_id, year)
            if team_id < 1 or team_id > len(league.teams):
                return f"Invalid team_id. Must be between 1 and {len(league.teams)}"
            team = league.teams[team_id - 1]
            roster_info = {
                "team_name": team.team_name,
                "owner": team.owners,
                "wins": team.wins,
                "losses": team.losses,
                "roster": [
                    {
                        "name": p.name,
                        "position": p.position,
                        "proTeam": p.proTeam,
                        "points": p.total_points,
                        "projected_points": p.projected_total_points,
                        "stats": p.stats,
                    }
                    for p in team.roster
                ],
            }
            return str(roster_info)
        except Exception as e:
            log_error(f"Error retrieving team roster: {str(e)}")
            if "401" in str(e) or "Private" in str(e):
                return (
                    "This appears to be a private league. Run the authenticate tool to login via browser.\n"
                    "After login, credentials (ESPN_S2 and SWID) will be displayed so you can update your connector env or .env."
                )
            return f"Error retrieving team roster: {str(e)}"

    @mcp.tool()
    async def get_team_info(league_id: int, team_id: int, year: int = CURRENT_YEAR) -> str:
        try:
            league = await league_service.get_league(league_id, year)
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
                "outcomes": team.outcomes,
            }
            return str(team_info)
        except Exception as e:
            log_error(f"Error retrieving team results: {str(e)}")
            if "401" in str(e) or "Private" in str(e):
                return (
                    "This appears to be a private league. Run the authenticate tool to login via browser.\n"
                    "After login, credentials (ESPN_S2 and SWID) will be displayed so you can update your connector env or .env."
                )
            return f"Error retrieving team results: {str(e)}"

    @mcp.tool()
    async def get_player_stats(league_id: int, player_name: str, year: int = CURRENT_YEAR) -> str:
        try:
            league = await league_service.get_league(league_id, year)
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
            stats = {
                "name": player.name,
                "position": player.position,
                "team": player.proTeam,
                "points": player.total_points,
                "projected_points": player.projected_total_points,
                "stats": player.stats,
                "injured": player.injured,
            }
            return str(stats)
        except Exception as e:
            log_error(f"Error retrieving player stats: {str(e)}")
            if "401" in str(e) or "Private" in str(e):
                return (
                    "This appears to be a private league. Run the authenticate tool to login via browser.\n"
                    "After login, credentials (ESPN_S2 and SWID) will be displayed so you can update your connector env or .env."
                )
            return f"Error retrieving player stats: {str(e)}"

    @mcp.tool()
    async def get_league_standings(league_id: int, year: int = CURRENT_YEAR) -> str:
        try:
            league = await league_service.get_league(league_id, year)
            sorted_teams = sorted(league.teams, key=lambda x: (x.wins, x.points_for), reverse=True)
            standings = []
            for i, team in enumerate(sorted_teams):
                standings.append(
                    {
                        "rank": i + 1,
                        "team_name": team.team_name,
                        "owner": team.owners,
                        "wins": team.wins,
                        "losses": team.losses,
                        "points_for": team.points_for,
                        "points_against": team.points_against,
                    }
                )
            return str(standings)
        except Exception as e:
            log_error(f"Error retrieving league standings: {str(e)}")
            if "401" in str(e) or "Private" in str(e):
                return (
                    "This appears to be a private league. Run the authenticate tool to login via browser.\n"
                    "After login, credentials (ESPN_S2 and SWID) will be displayed so you can update your connector env or .env."
                )
            return f"Error retrieving league standings: {str(e)}"

    @mcp.tool()
    async def get_matchup_info(league_id: int, week: int | None = None, year: int = CURRENT_YEAR) -> str:
        try:
            league = await league_service.get_league(league_id, year)
            if week is None:
                week = league.current_week
            if week < 1 or week > 17:
                return "Invalid week number. Must be between 1 and 17"
            matchups = league.box_scores(week)
            matchup_info = []
            for matchup in matchups:
                matchup_info.append(
                    {
                        "home_team": matchup.home_team.team_name,
                        "home_score": matchup.home_score,
                        "away_team": matchup.away_team.team_name if matchup.away_team else "BYE",
                        "away_score": matchup.away_score if matchup.away_team else 0,
                        "winner": "HOME" if matchup.home_score > matchup.away_score else "AWAY" if matchup.away_score > matchup.home_score else "TIE",
                    }
                )
            return str(matchup_info)
        except Exception as e:
            log_error(f"Error retrieving matchup information: {str(e)}")
            if "401" in str(e) or "Private" in str(e):
                return (
                    "This appears to be a private league. Run the authenticate tool to login via browser.\n"
                    "After login, credentials (ESPN_S2 and SWID) will be displayed so you can update your connector env or .env."
                )
            return f"Error retrieving matchup information: {str(e)}"


