# ESPN Fantasy Football MCP Server

## Overview

This MCP (Model Context Protocol) server allows LLMs to interact with the ESPN Fantasy Football API. It provides tools for accessing league data, team rosters, player statistics, and more through a standardized interface. It can work with both public and private ESPN Leagues.

This project is forked from [KBThree13/mcp_espn_ff](https://github.com/KBThree13/mcp_espn_ff). It expands on that project by adding compatibilty with other LLM clients, such as Perplexity, and adds an authentication tool so that users can easily find their authentication tokens from ESPN.

## Features (MCP Tools)

- **Authentication**: Open a browser for user to sign-in so that they can automatically find authentication tokens. Tokens can be stored in the LLM client or in a .env file.
- **League Info**: Get basic information about fantasy football leagues
- **Team Rosters**: View current team rosters and player details
- **Player Stats**: Find and display stats for specific players
- **League Standings**: View current team rankings and performance metrics
- **Matchup Information**: Get details about weekly matchups

## Installation

### Prerequisites

- Python 3.10 or higher
- `uv` package manager
  - espn-api >= 0.44.1
  - mcp[cli] >=1.5.0
  - playwright >=1.45.0
  - python-dotenv >=1.0.1


## Usage with LLM Clients

### Perplexity

1. Add MCP_ESPN_FF as a [connector in Perplexity](https://www.perplexity.ai/search/how-do-i-add-a-connector-the-p-O2JTAQUFRiKI68X_4N43ww).

2. Add the following environment variables as part of the connector (case sensitive):
  - "espn_s2"
  - "SWID"

  If you already know these tokens, you can add them or ask the connector to authencticate and print the tokens. (Recommend you delete the chat later).


### Claude Desktop

1. Update the Claude Desktop config:
- MacOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Include reference to the MCP server
  ```json
  {
    "args" : [
      "--directory",
      "/Users/morgankeys/gits/mcp_espn_ff",
      "run",
      "server.py"
    ],
    "command" : "uv",
    "env" : {
      "SWID" : "<value>",
      "espn_s2" : "<value>"
    }
  }
  ```
2. Restart Claude Desktop


## Acknowledgements
- [KBThree13/mcp_espn_ff](https://github.com/KBThree13/mcp_espn_ff) - The repo this project is forked from
- [cwendt94/espn-api](https://github.com/cwendt94/espn-api) - Nifty python wrapper around the ESPN Fantasy API