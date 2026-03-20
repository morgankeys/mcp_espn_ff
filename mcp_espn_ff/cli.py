"""
ESPN Fantasy Football CLI — used by Claude Code skills.

Each subcommand mirrors one of the original MCP tools, but runs as a
standalone process that prints human-readable (or JSON) output to stdout.

Usage examples:
    python -m mcp_espn_ff.cli league-info --league-id 12345
    python -m mcp_espn_ff.cli standings   --league-id 12345 --year 2024
    python -m mcp_espn_ff.cli roster      --league-id 12345 --team-id 3
    python -m mcp_espn_ff.cli team-info   --league-id 12345 --team-id 3
    python -m mcp_espn_ff.cli player      --league-id 12345 --name "Mahomes"
    python -m mcp_espn_ff.cli matchups    --league-id 12345 --week 5
    python -m mcp_espn_ff.cli authenticate
"""

import argparse
import asyncio
import datetime
import json
import sys

from .espn_service import LeagueService, ensure_authenticated

CURRENT_YEAR = datetime.datetime.now().year
if datetime.datetime.now().month < 7:
    CURRENT_YEAR -= 1

_league_service = LeagueService()


def _out(data) -> None:
    """Print dict/list as pretty JSON, or plain string as-is."""
    if isinstance(data, (dict, list)):
        print(json.dumps(data, indent=2, default=str))
    else:
        print(data)


def _private_league_hint(err: Exception) -> bool:
    return "401" in str(err) or "Private" in str(err)


# ---------------------------------------------------------------------------
# Subcommand implementations
# ---------------------------------------------------------------------------

async def cmd_authenticate(_args) -> int:
    try:
        espn_s2, swid, _state = await ensure_authenticated(persist_mode="dot_env")
        _out({
            "status": "authenticated",
            "ESPN_S2": espn_s2,
            "SWID": swid,
            "note": "Credentials saved to .env and active for this session.",
        })
        return 0
    except Exception as e:
        _out({"error": str(e)})
        return 1


async def cmd_league_info(args) -> int:
    try:
        league = await _league_service.get_league(args.league_id, args.year)
        _out({
            "name": league.settings.name,
            "year": league.year,
            "current_week": league.current_week,
            "nfl_week": league.nfl_week,
            "team_count": len(league.teams),
            "teams": [t.team_name for t in league.teams],
            "scoring_type": league.settings.scoring_type,
        })
        return 0
    except Exception as e:
        if _private_league_hint(e):
            _out({"error": "private_league", "hint": "Run: python -m mcp_espn_ff.cli authenticate"})
        else:
            _out({"error": str(e)})
        return 1


async def cmd_standings(args) -> int:
    try:
        league = await _league_service.get_league(args.league_id, args.year)
        sorted_teams = sorted(league.teams, key=lambda t: (t.wins, t.points_for), reverse=True)
        _out([
            {
                "rank": i + 1,
                "team_name": t.team_name,
                "owner": t.owners,
                "wins": t.wins,
                "losses": t.losses,
                "points_for": t.points_for,
                "points_against": t.points_against,
            }
            for i, t in enumerate(sorted_teams)
        ])
        return 0
    except Exception as e:
        if _private_league_hint(e):
            _out({"error": "private_league", "hint": "Run: python -m mcp_espn_ff.cli authenticate"})
        else:
            _out({"error": str(e)})
        return 1


async def cmd_roster(args) -> int:
    try:
        league = await _league_service.get_league(args.league_id, args.year)
        if args.team_id < 1 or args.team_id > len(league.teams):
            _out({"error": f"team_id must be 1–{len(league.teams)}"})
            return 1
        team = league.teams[args.team_id - 1]
        _out({
            "team_name": team.team_name,
            "owner": team.owners,
            "wins": team.wins,
            "losses": team.losses,
            "roster": [
                {
                    "name": p.name,
                    "position": p.position,
                    "pro_team": p.proTeam,
                    "points": p.total_points,
                    "projected_points": p.projected_total_points,
                }
                for p in team.roster
            ],
        })
        return 0
    except Exception as e:
        if _private_league_hint(e):
            _out({"error": "private_league", "hint": "Run: python -m mcp_espn_ff.cli authenticate"})
        else:
            _out({"error": str(e)})
        return 1


async def cmd_team_info(args) -> int:
    try:
        league = await _league_service.get_league(args.league_id, args.year)
        if args.team_id < 1 or args.team_id > len(league.teams):
            _out({"error": f"team_id must be 1–{len(league.teams)}"})
            return 1
        t = league.teams[args.team_id - 1]
        _out({
            "team_name": t.team_name,
            "owner": t.owners,
            "wins": t.wins,
            "losses": t.losses,
            "ties": t.ties,
            "points_for": t.points_for,
            "points_against": t.points_against,
            "acquisitions": t.acquisitions,
            "drops": t.drops,
            "trades": t.trades,
            "playoff_pct": t.playoff_pct,
            "final_standing": t.final_standing,
            "outcomes": t.outcomes,
        })
        return 0
    except Exception as e:
        if _private_league_hint(e):
            _out({"error": "private_league", "hint": "Run: python -m mcp_espn_ff.cli authenticate"})
        else:
            _out({"error": str(e)})
        return 1


async def cmd_player(args) -> int:
    try:
        league = await _league_service.get_league(args.league_id, args.year)
        found = None
        for team in league.teams:
            for p in team.roster:
                if args.name.lower() in p.name.lower():
                    found = p
                    break
            if found:
                break
        if not found:
            _out({"error": f"Player '{args.name}' not found in league {args.league_id}"})
            return 1
        _out({
            "name": found.name,
            "position": found.position,
            "pro_team": found.proTeam,
            "points": found.total_points,
            "projected_points": found.projected_total_points,
            "injured": found.injured,
            "stats": found.stats,
        })
        return 0
    except Exception as e:
        if _private_league_hint(e):
            _out({"error": "private_league", "hint": "Run: python -m mcp_espn_ff.cli authenticate"})
        else:
            _out({"error": str(e)})
        return 1


async def cmd_matchups(args) -> int:
    try:
        league = await _league_service.get_league(args.league_id, args.year)
        week = args.week if args.week is not None else league.current_week
        if week < 1 or week > 17:
            _out({"error": "week must be 1–17"})
            return 1
        matchups = league.box_scores(week)
        _out([
            {
                "home_team": m.home_team.team_name,
                "home_score": m.home_score,
                "away_team": m.away_team.team_name if m.away_team else "BYE",
                "away_score": m.away_score if m.away_team else 0,
                "winner": (
                    "HOME" if m.home_score > m.away_score
                    else "AWAY" if m.away_score > m.home_score
                    else "TIE"
                ),
            }
            for m in matchups
        ])
        return 0
    except Exception as e:
        if _private_league_hint(e):
            _out({"error": "private_league", "hint": "Run: python -m mcp_espn_ff.cli authenticate"})
        else:
            _out({"error": str(e)})
        return 1


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m mcp_espn_ff.cli",
        description="ESPN Fantasy Football CLI",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # authenticate
    sub.add_parser("authenticate", help="Open browser to log in to ESPN and save credentials.")

    # league-info
    p = sub.add_parser("league-info", help="Show basic league info.")
    p.add_argument("--league-id", type=int, required=True)
    p.add_argument("--year", type=int, default=CURRENT_YEAR)

    # standings
    p = sub.add_parser("standings", help="Show league standings.")
    p.add_argument("--league-id", type=int, required=True)
    p.add_argument("--year", type=int, default=CURRENT_YEAR)

    # roster
    p = sub.add_parser("roster", help="Show a team's roster.")
    p.add_argument("--league-id", type=int, required=True)
    p.add_argument("--team-id", type=int, required=True)
    p.add_argument("--year", type=int, default=CURRENT_YEAR)

    # team-info
    p = sub.add_parser("team-info", help="Show team season stats.")
    p.add_argument("--league-id", type=int, required=True)
    p.add_argument("--team-id", type=int, required=True)
    p.add_argument("--year", type=int, default=CURRENT_YEAR)

    # player
    p = sub.add_parser("player", help="Look up a player's stats (fuzzy name search).")
    p.add_argument("--league-id", type=int, required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--year", type=int, default=CURRENT_YEAR)

    # matchups
    p = sub.add_parser("matchups", help="Show matchups for a week.")
    p.add_argument("--league-id", type=int, required=True)
    p.add_argument("--week", type=int, default=None, help="Defaults to current week.")
    p.add_argument("--year", type=int, default=CURRENT_YEAR)

    return parser


COMMANDS = {
    "authenticate": cmd_authenticate,
    "league-info": cmd_league_info,
    "standings": cmd_standings,
    "roster": cmd_roster,
    "team-info": cmd_team_info,
    "player": cmd_player,
    "matchups": cmd_matchups,
}


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    handler = COMMANDS[args.command]
    exit_code = asyncio.run(handler(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
