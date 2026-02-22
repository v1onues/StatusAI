"""
main.py — StatusAI Storyteller Orchestrator v3
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Multi-source activity tracking → Storyteller AI → Discord Rich Presence.
Turns your Discord profile into a live Entrepreneur's Journal.

Usage:
    python main.py
"""

import json
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
except ImportError:
    class _NoColor:
        def __getattr__(self, _): return ""
    Fore = Style = _NoColor()

from discord_rpc import DiscordRPC
from trackers import get_full_context, FullContext
from ai_engine import generate_status, get_stats


# ──────────────────────────────────────────────
#  Constants
# ──────────────────────────────────────────────

VERSION = "3.0.0"
CONFIG_FILE = "config.json"
LOG_FILE = "status_history.log"

PERSONA_ICONS = {
    "hacker": "👾", "sigma": "🐺", "chill": "☕",
    "gamer": "🎮", "poet": "📝", "custom": "⚡",
}


# ──────────────────────────────────────────────
#  Startup
# ──────────────────────────────────────────────

def print_banner():
    frames = [
        f"{Fore.CYAN}  ⠋ Başlatılıyor...{Style.RESET_ALL}",
        f"{Fore.CYAN}  ⠙ Başlatılıyor...{Style.RESET_ALL}",
        f"{Fore.CYAN}  ⠹ Başlatılıyor...{Style.RESET_ALL}",
        f"{Fore.CYAN}  ⠸ Başlatılıyor...{Style.RESET_ALL}",
        f"{Fore.CYAN}  ⠼ Başlatılıyor...{Style.RESET_ALL}",
        f"{Fore.CYAN}  ⠴ Başlatılıyor...{Style.RESET_ALL}",
        f"{Fore.CYAN}  ⠦ Başlatılıyor...{Style.RESET_ALL}",
        f"{Fore.CYAN}  ⠧ Başlatılıyor...{Style.RESET_ALL}",
    ]
    for i in range(16):
        sys.stdout.write(f"\r{frames[i % len(frames)]}")
        sys.stdout.flush()
        time.sleep(0.08)
    sys.stdout.write("\r" + " " * 40 + "\r")
    sys.stdout.flush()

    print(f"""
{Fore.CYAN}  ┌──────────────────────────────────────────────┐
  │                                              │
  │   {Fore.WHITE}⚡ S T A T U S  A I{Fore.CYAN}                        │
  │   {Fore.WHITE}   Storyteller Engine v{VERSION}{Fore.CYAN}              │
  │   {Fore.WHITE}   Multi-Source • AI-Powered{Fore.CYAN}                │
  │                                              │
  └──────────────────────────────────────────────┘{Style.RESET_ALL}
""")


# ──────────────────────────────────────────────
#  Config
# ──────────────────────────────────────────────

class ConfigManager:
    def __init__(self):
        self._config: dict = {}
        self._path = Path(__file__).parent / CONFIG_FILE
        self._last_modified: float = 0

    def load(self) -> dict:
        if not self._path.exists():
            _fatal(f"'{CONFIG_FILE}' bulunamadı!")
        try:
            with open(self._path, "r", encoding="utf-8") as f:
                self._config = json.load(f)
        except json.JSONDecodeError as e:
            _fatal(f"config.json parse hatası: {e}")

        for key in ["discord_client_id", "ai_api_key"]:
            value = self._config.get(key, "")
            if not value or value.startswith("YOUR_"):
                _fatal(f"config.json'da '{key}' alanını doldurun!")

        self._config.setdefault("ai_provider", "gemini")
        self._config.setdefault("ai_model", "gemini-2.0-flash")
        self._config.setdefault("update_interval", 20)
        self._config.setdefault("fallback_status", "💤 AFK — Birazdan dönerim.")
        self._config.setdefault("tracked_apps", {})
        self._config.setdefault("persona", "custom")
        self._config.setdefault("language", "tr")
        self._config.setdefault("show_button", False)

        self._last_modified = self._path.stat().st_mtime
        return self._config

    def check_reload(self) -> bool:
        try:
            mtime = self._path.stat().st_mtime
            if mtime > self._last_modified:
                self.load()
                return True
        except Exception:
            pass
        return False

    @property
    def config(self) -> dict:
        return self._config


# ──────────────────────────────────────────────
#  Logger
# ──────────────────────────────────────────────

class ActivityLogger:
    def __init__(self):
        self._path = Path(__file__).parent / LOG_FILE

    def log(self, context_str: str, status: str):
        try:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(f"[{ts}] {context_str} → \"{status}\"\n")
        except Exception:
            pass


def _log(icon: str, msg: str):
    ts = time.strftime("%H:%M:%S")
    print(f"  {Fore.WHITE}{ts}  {icon}  {msg}{Style.RESET_ALL}")

def _info(msg: str):
    _log(f"{Fore.CYAN}ℹ", f"{Fore.CYAN}{msg}")

def _success(msg: str):
    _log(f"{Fore.GREEN}✔", f"{Fore.GREEN}{msg}")

def _warn(msg: str):
    _log(f"{Fore.YELLOW}⚠", f"{Fore.YELLOW}{msg}")

def _error(msg: str):
    _log(f"{Fore.RED}✖", f"{Fore.RED}{msg}")

def _status_log(msg: str):
    _log(f"{Fore.MAGENTA}♦", f"{Fore.MAGENTA}{msg}")

def _fatal(msg: str):
    print(f"\n  {Fore.RED}✖  HATA: {msg}{Style.RESET_ALL}\n")
    sys.exit(1)

def _divider():
    print(f"  {Fore.CYAN}{'─' * 48}{Style.RESET_ALL}")

def _print_stats(config: dict):
    ai = get_stats()
    persona = config.get("persona", "custom")
    icon = PERSONA_ICONS.get(persona, "⚡")
    print(f"""
  {Fore.CYAN}┌─── Stats ────────────────────────────────────┐{Style.RESET_ALL}
  {Fore.CYAN}│{Style.RESET_ALL}  {icon} Persona: {Fore.WHITE}{persona.upper()}{Style.RESET_ALL}
  {Fore.CYAN}│{Style.RESET_ALL}  🤖 Provider: {Fore.WHITE}{config.get('ai_provider', '?').upper()}{Style.RESET_ALL}
  {Fore.CYAN}│{Style.RESET_ALL}  ⏱️  Uptime: {Fore.WHITE}{ai.uptime}{Style.RESET_ALL}
  {Fore.CYAN}│{Style.RESET_ALL}  📊 AI Calls: {Fore.GREEN}{ai.successful_calls}{Style.RESET_ALL}/{ai.total_calls} ({ai.success_rate})
  {Fore.CYAN}│{Style.RESET_ALL}  💾 Cache: {Fore.YELLOW}{ai.cache_hits}{Style.RESET_ALL}
  {Fore.CYAN}└──────────────────────────────────────────────┘{Style.RESET_ALL}
""")


# ──────────────────────────────────────────────
#  Discord RPC
# ──────────────────────────────────────────────

def connect_rpc(client_id: str) -> DiscordRPC:
    rpc = DiscordRPC(client_id)
    max_retries = 5
    delay = 3

    for attempt in range(1, max_retries + 1):
        try:
            _info(f"Discord RPC'ye bağlanılıyor... (deneme {attempt}/{max_retries})")
            rpc.connect()
            _success("Discord RPC bağlantısı kuruldu!")
            return rpc
        except Exception as e:
            _warn(f"Bağlantı başarısız: {e}")
            if attempt < max_retries:
                _info(f"{delay}s sonra tekrar denenecek...")
                time.sleep(delay)
                delay = min(delay * 2, 30)
            else:
                _fatal(
                    "Discord'a bağlanılamadı!\n"
                    "  1. Discord açık mı?\n"
                    "  2. discord_client_id doğru mu?"
                )

    raise RuntimeError("RPC bağlantısı kurulamadı.")


# ──────────────────────────────────────────────
#  Main Loop
# ──────────────────────────────────────────────

def main_loop(rpc: DiscordRPC, config_mgr: ConfigManager):
    config = config_mgr.config
    interval = max(15, min(60, config.get("update_interval", 20)))
    tracked_apps = config.get("tracked_apps", {})
    last_ctx: FullContext | None = None
    current_status = ""
    offline_mode = False
    cycle = 0
    logger = ActivityLogger()

    persona = config.get("persona", "custom")
    icon = PERSONA_ICONS.get(persona, "⚡")

    _divider()
    _info(f"Güncelleme: {interval}s | AI: {config.get('ai_provider', 'gemini').upper()} | {icon} {persona.upper()}")
    _info(f"Takip: {len(tracked_apps)} uygulama | Mod: Storyteller Engine")
    _divider()
    _info("Ana döngü başlatıldı. Ctrl+C ile durdur.\n")

    while True:
        try:
            cycle += 1

            # Hot-reload
            if cycle % 5 == 0 and config_mgr.check_reload():
                config = config_mgr.config
                tracked_apps = config.get("tracked_apps", {})
                interval = max(15, min(60, config.get("update_interval", 20)))
                _success("🔄 Config yeniden yüklendi!")

            # ── 1. Multi-source context ──
            ctx = get_full_context(tracked_apps)

            # ── 2. Check for change ──
            if last_ctx is not None and not ctx.has_changed(last_ctx) and current_status:
                time.sleep(interval)
                continue

            # ── 3. Build context prompt ──
            context_prompt = ctx.build_prompt()
            _info(f"Bağlam: {context_prompt}")

            if ctx.running_apps:
                _info(f"Çalışan: {', '.join(ctx.running_apps)}")

            # ── 4. Status Generation (Template for media, AI for rest) ──
            if ctx.has_media:
                # Media detected → use template with literal titles
                new_status = ctx.build_direct_status()
                if not new_status:
                    new_status = generate_status(context_prompt, config)
            else:
                # No media → AI storytelling
                new_status = generate_status(context_prompt, config)

            if new_status != current_status:
                current_status = new_status
                _status_log(f"→ {current_status}")

                logger.log(context_prompt, current_status)

                # ── 5. Update Discord ──
                try:
                    # Build buttons
                    buttons = None
                    if config.get("show_button", False):
                        label = config.get("button_label", "⚡ StatusAI")
                        url = config.get("button_url", "")
                        if label and url:
                            buttons = [{"label": label, "url": url}]

                    # Determine details text
                    details = None
                    if ctx.game_name:
                        details = ctx.game_name
                    elif ctx.active_app and ctx.active_app != "Unknown":
                        details = ctx.active_app

                    # Dynamic app icon
                    APP_ICONS = {
                        "YouTube": "youtube",
                        "VS Code": "vscode",
                        "Spotify": "spotify",
                        "Discord": "discord",
                        "Chrome": "chrome",
                        "Telegram": "telegram",
                        "Steam": "steam",
                        "GitHub": "github",
                        "Twitch": "twitch",
                        "VALORANT": "valorant",
                        "League of Legends": "steam",
                        "CS2": "steam",
                        "CS:GO": "steam",
                    }
                    # Priority: game > browser platform > active app
                    icon = "logo"
                    if ctx.game_name and ctx.game_name in APP_ICONS:
                        icon = APP_ICONS[ctx.game_name]
                    elif ctx.browser_platform and ctx.browser_platform in APP_ICONS:
                        icon = APP_ICONS[ctx.browser_platform]
                    elif ctx.active_app and ctx.active_app in APP_ICONS:
                        icon = APP_ICONS[ctx.active_app]

                    rpc.update(
                        state=current_status,
                        details=details,
                        large_image=icon,
                        large_text=ctx.active_app or "StatusAI",
                        small_image="logo",
                        small_text=f"StatusAI v{VERSION}",
                        buttons=buttons,
                    )
                    _success("Discord güncellendi!")
                    if offline_mode:
                        offline_mode = False
                        _success("Online moda dönüldü!")
                except Exception as e:
                    _warn(f"RPC hatası: {e}")
                    offline_mode = True
                    _offline(rpc, config)

            last_ctx = ctx

            # Stats
            if cycle % 10 == 0:
                _print_stats(config)

            time.sleep(interval)

        except KeyboardInterrupt:
            break
        except Exception as e:
            _error(f"Hata: {e}")
            if not offline_mode:
                offline_mode = True
                _offline(rpc, config)
            time.sleep(interval)


def _offline(rpc: DiscordRPC, config: dict):
    fallback = config.get("fallback_status", "💤 AFK — Birazdan dönerim.")
    _warn(f"Offline → \"{fallback}\"")
    try:
        rpc.update(
            state=fallback,
            large_image="logo",
            large_text="StatusAI — Offline",
        )
    except Exception:
        pass


# ──────────────────────────────────────────────
#  Entry Point
# ──────────────────────────────────────────────

def main():
    print_banner()

    _info("Konfigürasyon yükleniyor...")
    config_mgr = ConfigManager()
    config = config_mgr.load()
    _success("config.json yüklendi!")

    persona = config.get("persona", "custom")
    icon = PERSONA_ICONS.get(persona, "⚡")
    _info(f"Persona: {icon} {persona.upper()}")

    rpc = connect_rpc(config["discord_client_id"])

    def shutdown(sig, frame):
        print()
        _divider()
        _warn("Kapatılıyor...")
        _print_stats(config)
        try:
            rpc.close()
            _success("Discord RPC kapatıldı.")
        except Exception:
            pass
        _info("StatusAI kapatıldı. Görüşürüz! 👋")
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        main_loop(rpc, config_mgr)
    except KeyboardInterrupt:
        shutdown(None, None)


if __name__ == "__main__":
    main()
