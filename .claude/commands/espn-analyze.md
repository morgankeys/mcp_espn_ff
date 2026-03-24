# ESPN Fantasy Football Analysis

Higher-order analysis that combines multiple data sources: trade advice, waiver
recommendations, playoff projections, and head-to-head comparisons.

## Usage

The user asks a strategic fantasy football question. Use this skill to chain
multiple CLI calls together and synthesize the results into actionable advice.

Always ask for **League ID** first. Collect other parameters as needed.

## Available data commands

```bash
# League overview & team list (gives you team IDs)
uv run python -m mcp_espn_ff.cli league-info --league-id <ID>

# Full standings
uv run python -m mcp_espn_ff.cli standings --league-id <ID>

# One team's roster (repeat for each team you want to compare)
uv run python -m mcp_espn_ff.cli roster --league-id <ID> --team-id <N>

# One team's season stats
uv run python -m mcp_espn_ff.cli team-info --league-id <ID> --team-id <N>

# Player lookup
uv run python -m mcp_espn_ff.cli player --league-id <ID> --name "<NAME>"

# Weekly matchups
uv run python -m mcp_espn_ff.cli matchups --league-id <ID> [--week <W>]
```

All commands accept `--year <YEAR>` (defaults to current season).

## Analysis workflows

### Trade evaluation
1. Fetch roster for both teams involved (`roster --team-id`).
2. Fetch player stats for key players being traded (`player --name`).
3. Assess: positional needs, points contribution, injury risk, schedule strength.
4. Give a clear verdict: who wins the trade and why.

### Waiver wire recommendations
1. Fetch the requesting team's roster.
2. Identify the weakest position by comparing actual vs. projected points.
3. Suggest which player to drop and why.
4. (If you have waiver data from the ESPN API, list top available players at that position.)

### Playoff projection
1. Fetch standings (wins, points for).
2. Fetch remaining matchups.
3. Estimate likely outcomes and who makes the playoffs.

### Head-to-head comparison
1. Fetch both teams' rosters.
2. Compare position-by-position: QB, RB, WR, TE, K, DEF.
3. Project a winner based on projected points and injury status.

### Season recap
1. Fetch standings.
2. Fetch team-info for all teams (loop over team IDs 1..N).
3. Summarize: most transactions, highest scorer, biggest overachiever vs. projections.

## Output style

- Lead with a clear, direct answer or recommendation.
- Support it with 2–3 specific data points from the CLI output.
- Keep it concise — fantasy managers want actionable insight, not raw numbers.
- If the output contains `"error": "private_league"`, tell the user to run `/espn-auth` first.
