import os
import sys
import asyncio
import time
from dataclasses import dataclass
from typing import Optional, Tuple, Literal


def log_error(message: str) -> None:
    print(message, file=sys.stderr)


# Load environment variables from a local .env file if present, without overriding process env
try:
    from dotenv import load_dotenv, find_dotenv

    env_path = find_dotenv()
    if env_path:
        load_dotenv(env_path, override=False)
        log_error(f"Loaded .env from {env_path}")
    else:
        log_error(".env not found; relying on process environment variables if set")
except Exception:
    # Safe to continue if python-dotenv is not installed
    pass


CredentialSource = Literal["process_env", "dot_env", "none"]


@dataclass
class AuthState:
    source: CredentialSource
    is_valid: bool
    last_checked: float
    masked: dict


def mask_secret(value: Optional[str], show_last: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= show_last:
        return "*" * len(value)
    return ("*" * (len(value) - show_last)) + value[-show_last:]


class CredentialManager:
    """Manages ESPN credentials from process env and optional .env persistence."""

    def __init__(self) -> None:
        self._memory: dict[str, Optional[str]] = {"ESPN_S2": None, "SWID": None}

    def get(self) -> Tuple[Optional[str], Optional[str], AuthState]:
        # Read from process environment with support for common aliases
        env_espn_s2 = os.environ.get("ESPN_S2") or os.environ.get("espn_s2")
        env_swid = os.environ.get("SWID") or os.environ.get("swid")

        # Memory takes precedence only if explicitly set for current run
        espn_s2 = self._memory.get("ESPN_S2") or env_espn_s2
        swid = self._memory.get("SWID") or env_swid

        # Infer source based on where non-empty values exist
        source: CredentialSource = "none"
        if env_espn_s2 and env_swid:
            source = "process_env"
        elif espn_s2 and swid:
            # Values came from memory (populated via dotenv earlier) but process env lacks them
            source = "dot_env"

        is_valid = bool(espn_s2) and bool(swid)
        state = AuthState(
            source=source,
            is_valid=is_valid,
            last_checked=time.time(),
            masked={
                "espn_s2": mask_secret(espn_s2),
                "SWID": mask_secret(swid),
            },
        )
        return espn_s2, swid, state

    def set(self, espn_s2: str, swid: str, persist_mode: Literal["memory", "env", "dot_env"] = "env") -> None:
        # Always set memory for current run
        self._memory["espn_s2"] = espn_s2
        self._memory["SWID"] = swid

        if persist_mode in ("env", "dot_env"):
            try:
                os.environ["espn_s2"] = espn_s2
                os.environ["SWID"] = swid
            except Exception:
                pass

        if persist_mode == "dot_env":
            self._write_dotenv(espn_s2, swid)

    def _write_dotenv(self, espn_s2: str, swid: str) -> None:
        path = os.path.join(os.getcwd(), ".env")
        lines: list[str] = []
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    lines = f.read().splitlines()
        except Exception:
            lines = []

        def upsert(lines: list[str], key: str, value: str) -> list[str]:
            found = False
            new_lines = []
            for line in lines:
                if line.startswith(f"{key}="):
                    new_lines.append(f"{key}={value}")
                    found = True
                else:
                    new_lines.append(line)
            if not found:
                new_lines.append(f"{key}={value}")
            return new_lines

        lines = upsert(lines, "ESPN_S2", espn_s2)
        lines = upsert(lines, "SWID", swid)
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


_auth_lock = asyncio.Lock()
_credential_manager = CredentialManager()


async def authenticate_browser(timeout_seconds: int = 180, headless: bool = False) -> Tuple[str, str]:
    try:
        from playwright.async_api import async_playwright
    except Exception as import_err:
        log_error(f"Playwright import failed: {str(import_err)}")
        raise RuntimeError(
            "Playwright is required for browser authentication. Install browsers with: python -m playwright install chromium"
        )

    async with _auth_lock:
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(headless=headless)
            except Exception as launch_err:
                msg = (
                    "Failed to launch Chromium. You may need to install Playwright browsers. "
                    "Run: python -m playwright install chromium"
                )
                log_error(f"{msg} | Details: {str(launch_err)}")
                raise RuntimeError(msg)

            context = await browser.new_context()
            page = await context.new_page()
            await page.goto("https://www.espn.com/fantasy/football/")

            loop = asyncio.get_event_loop()
            deadline = loop.time() + timeout_seconds
            found_espn_s2 = None
            found_swid = None

            log_error("Please log into ESPN in the opened browser window...")
            try:
                while loop.time() < deadline:
                    cookies = await context.cookies()
                    for cookie in cookies:
                        name = cookie.get("name")
                        if name == "espn_s2" and not found_espn_s2:
                            found_espn_s2 = cookie.get("value")
                        if name == "SWID" and not found_swid:
                            found_swid = cookie.get("value")
                    if found_espn_s2 and found_swid:
                        break
                    await asyncio.sleep(0.5)
            finally:
                await browser.close()

            if not (found_espn_s2 and found_swid):
                raise TimeoutError(
                    "Timed out waiting for login. Please log into ESPN in the opened browser window, then retry."
                )

            return found_espn_s2, found_swid


async def ensure_authenticated(headless: bool = False, persist_mode: Literal["memory", "env", "dot_env"] = "env") -> Tuple[str, str, AuthState]:
    espn_s2, swid, state = _credential_manager.get()
    if state.is_valid:
        return espn_s2 or "", swid or "", state

    # Acquire via browser
    new_espn_s2, new_swid = await authenticate_browser(headless=headless)
    _credential_manager.set(new_espn_s2, new_swid, persist_mode=persist_mode)
    espn_s2, swid, state = _credential_manager.get()
    return espn_s2 or "", swid or "", state


def get_credential_manager() -> CredentialManager:
    return _credential_manager


