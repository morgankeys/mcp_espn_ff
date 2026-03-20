# ESPN Authentication

Opens a browser so you can log in to ESPN and saves the credentials to `.env`.

## When to use this skill

Run this when ESPN API calls return a "private league" or 401 error, or when no
credentials exist in the environment.

## Steps

1. Tell the user what's about to happen:
   > "I'll open a Chromium browser window. Please log in to your ESPN account there. I'll detect the cookies automatically."

2. Run:
   ```bash
   cd $PROJECT_ROOT && uv run python -m mcp_espn_ff.cli authenticate
   ```

3. The command will block until the user logs in (up to 3 minutes). If it times out, let the user know and suggest they retry.

4. On success the output contains `ESPN_S2` and `SWID` values. Tell the user:
   - Credentials are saved to `.env` automatically.
   - They can also copy the values into their environment or CI secrets if needed.

5. If there is an error, show it to the user and suggest running `python -m playwright install chromium` if Playwright is not installed.
