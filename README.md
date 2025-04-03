# ESPN Fantasy Football MCP Server

## Overview

This MCP (Model Context Protocol) server allows LLMs like Claude to interact with the ESPN Fantasy Football API. It provides tools for accessing league data, team rosters, player statistics, and more through a standardized interface.

## Features (MCP Tools)

- **Authentication**: Securely store ESPN credentials for the current session
- **League Info**: Get basic information about fantasy football leagues
- **Team Rosters**: View current team rosters and player details
- **Player Stats**: Find and display stats for specific players
- **League Standings**: View current team rankings and performance metrics
- **Matchup Information**: Get details about weekly matchups

## Installation

### Prerequisites

- Python 3.12 or higher
- [Claude Desktop](https://claude.ai/download) for the best experience

### Usage with Claude Desktop

1. Update the Claude Desktop config:
- MacOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Include reference to the MCP server
  ```json
  {
  "mcpServers": {
    "espn-fantasy-football": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/directory",
        "run",
        "espn_fantasy_server.py"
        ]
      }
    } 
  }
2. Restart Claude Desktop

## Acknoledgements

[cwendt94/espn-api](https://github.com/cwendt94/espn-api) for the nifty python wrapper around the ESPN Fantasy API
