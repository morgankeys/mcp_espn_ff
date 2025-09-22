import sys
from typing import Tuple
from espn_api.football import League
from .auth import ensure_authenticated


def log_error(message: str) -> None:
    print(message, file=sys.stderr)


class LeagueService:
    def __init__(self) -> None:
        self._cache: dict[Tuple[int, int], League] = {}
        self._last_creds: Tuple[str, str] | None = None

    async def get_league(self, league_id: int, year: int) -> League:
        espn_s2, swid, _ = await ensure_authenticated()

        # Invalidate cache if credentials changed
        current_creds = (espn_s2, swid)
        if self._last_creds is not None and self._last_creds != current_creds:
            self._cache.clear()
        self._last_creds = current_creds

        key = (league_id, year)
        if key not in self._cache:
            log_error(f"Creating new league instance for {league_id}, year {year}")
            self._cache[key] = League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)
        return self._cache[key]


