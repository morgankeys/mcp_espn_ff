# ESPN Roster & Player Stats

Look up a team's full roster or search for a specific player's stats.

## Usage

Ask the user for:
- **League ID** (required)
- **Team ID** (required for roster — numbered 1..N, visible in league standings output)
- **Player name** (for player lookup — partial/fuzzy match is supported)
- **Year** (optional, defaults to current season)

Tip: If the user doesn't know their team ID, run the standings command first
(`/espn-league`) — teams are listed in rank order and their position in that list
is their team ID.

## Commands

### Full team roster
```bash
cd $PROJECT_ROOT && uv run python -m mcp_espn_ff.cli roster --league-id <LEAGUE_ID> --team-id <TEAM_ID> [--year <YEAR>]
```

### Team season stats (W-L, points for/against, trades, playoff %)
```bash
cd $PROJECT_ROOT && uv run python -m mcp_espn_ff.cli team-info --league-id <LEAGUE_ID> --team-id <TEAM_ID> [--year <YEAR>]
```

### Individual player stats (fuzzy name search across all rosters)
```bash
cd $PROJECT_ROOT && uv run python -m mcp_espn_ff.cli player --league-id <LEAGUE_ID> --name "<PLAYER_NAME>" [--year <YEAR>]
```

## Interpreting results

- **Roster**: list each player with position, pro team, actual points, and projected points.
  Flag any injured players.
- **Team info**: summarize wins/losses, scoring pace, activity (acquisitions, drops, trades),
  and playoff outlook.
- **Player**: show points vs. projected and injury status. Note if they are significantly
  over/under-performing projections.
- If the output contains `"error": "private_league"`, tell the user to run `/espn-auth` first.

## Example follow-up analysis

- "Who is the weakest position on this roster?" — compare projected vs. actual by position.
- "Should I drop this player?" — look at injury status, points trend, and available alternatives.
- "Compare my roster to my opponent's" — fetch both rosters and compare position-by-position.
