# ESPN League Overview

Retrieve league info, standings, or weekly matchups from an ESPN Fantasy Football league.

## Usage

When the user asks about their league, standings, or matchups, ask for:
- **League ID** (required) — found in the ESPN URL: `fantasy.espn.com/football/league?leagueId=XXXXX`
- **Year** (optional, defaults to current season)
- **Week** (for matchups only, optional — defaults to current week)

## Commands

### League info (name, teams, scoring type, current week)
```bash
cd $PROJECT_ROOT && uv run python -m mcp_espn_ff.cli league-info --league-id <LEAGUE_ID> [--year <YEAR>]
```

### Standings (ranked by wins, then points)
```bash
cd $PROJECT_ROOT && uv run python -m mcp_espn_ff.cli standings --league-id <LEAGUE_ID> [--year <YEAR>]
```

### Matchups for a week
```bash
cd $PROJECT_ROOT && uv run python -m mcp_espn_ff.cli matchups --league-id <LEAGUE_ID> [--week <WEEK>] [--year <YEAR>]
```

## Interpreting results

- All output is JSON. Parse and summarize it for the user in plain language.
- For standings: present as a numbered table with W-L record and points scored.
- For matchups: show home vs. away with scores and who won.
- If the output contains `"error": "private_league"`, tell the user to run `/espn-auth` first.

## Example follow-up analysis

After fetching data, offer to:
- Identify the top scorer or biggest upset of the week (matchups).
- Highlight any teams on win/loss streaks (standings).
- Compare two specific teams head-to-head by fetching both rosters with `/espn-roster`.
