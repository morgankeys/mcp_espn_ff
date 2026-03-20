# ESPN Fantasy Football — Claude Code Skills

Query and analyze your ESPN Fantasy Football league directly from Claude Code using slash commands.

This project is forked from [KBThree13/mcp_espn_ff](https://github.com/KBThree13/mcp_espn_ff).

## Features

| Skill | Command | What it does |
|-------|---------|--------------|
| Authentication | `/espn-auth` | Opens a browser to log in to ESPN and saves credentials to `.env` |
| League overview | `/espn-league` | League info, standings, weekly matchups |
| Roster & players | `/espn-roster` | Team rosters, individual player stats, team season info |
| Analysis | `/espn-analyze` | Trade advice, waiver picks, playoff projections, head-to-head comparisons |

## Prerequisites

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) package manager
- Claude Code

## Installation

```bash
git clone https://github.com/morgankeys/mcp_espn_ff
cd mcp_espn_ff
uv sync
python -m playwright install chromium
```

## Authentication

ESPN credentials (`ESPN_S2` and `SWID`) are required for private leagues.

**Option A — browser login (recommended):**
Run `/espn-auth` in Claude Code. A Chromium window will open; log in and credentials
are saved to `.env` automatically.

**Option B — manual:**
Create a `.env` file in the project root:
```
ESPN_S2=<your value>
SWID=<your value>
```
You can find these values in your browser cookies after logging in to ESPN.

Public leagues work without any credentials.

## CLI reference

The skills use an underlying CLI that you can also call directly:

```bash
uv run python -m mcp_espn_ff.cli league-info --league-id <ID>
uv run python -m mcp_espn_ff.cli standings   --league-id <ID> [--year <YEAR>]
uv run python -m mcp_espn_ff.cli matchups    --league-id <ID> [--week <WEEK>]
uv run python -m mcp_espn_ff.cli roster      --league-id <ID> --team-id <N>
uv run python -m mcp_espn_ff.cli team-info   --league-id <ID> --team-id <N>
uv run python -m mcp_espn_ff.cli player      --league-id <ID> --name "<NAME>"
uv run python -m mcp_espn_ff.cli authenticate
```

All commands output JSON. Add `--help` to any subcommand for details.

Your **League ID** is in the ESPN URL: `fantasy.espn.com/football/league?leagueId=XXXXX`

## Acknowledgements

- [KBThree13/mcp_espn_ff](https://github.com/KBThree13/mcp_espn_ff) — original MCP server this project is forked from
- [cwendt94/espn-api](https://github.com/cwendt94/espn-api) — Python wrapper for the ESPN Fantasy API
