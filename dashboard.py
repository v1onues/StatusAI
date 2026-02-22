"""
dashboard.py — StatusAI Native Desktop Dashboard
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Native desktop window (pywebview) with embedded web UI.
Bot engine runs as a background thread.
Minimizes to system tray on close; fully quit via tray menu.
Can be packaged as .exe with PyInstaller.

Usage:
    python dashboard.py
"""

import json
import os
import os
import sys
import threading
import time
import webbrowser
import psutil
from datetime import datetime
from pathlib import Path
from queue import Queue, Empty

from flask import Flask, render_template, request, jsonify, Response
import setup_updater

# ──────────────────────────────────────────────
#  StatusAI Imports
# ──────────────────────────────────────────────

from discord_rpc import DiscordRPC
from trackers import get_full_context, FullContext
from ai_engine import generate_status, get_stats


# ──────────────────────────────────────────────
#  Constants
# ──────────────────────────────────────────────
# Determine the true base directory (where the .exe is running from, not the Temp extraction folder)
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent

VERSION = "3.0.0"
CONFIG_FILE = BASE_DIR / "config.json"
LOG_FILE = BASE_DIR / "status_history.log"
PORT = 3131

PERSONA_ICONS = {
    "hacker": "👾",
    "sigma": "🐺",
    "chill": "☕",
    "gamer": "🎮",
    "poet": "📝",
    "custom": "⚡",
}

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


# ──────────────────────────────────────────────
#  SSE Log Bus
# ──────────────────────────────────────────────


class LogBus:
    """Thread-safe log message bus with SSE support."""

    def __init__(self):
        self._subscribers: list[Queue] = []
        self._lock = threading.Lock()

    def subscribe(self) -> Queue:
        q: Queue = Queue(maxsize=200)
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: Queue):
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def emit(self, log_type: str, msg: str):
        ts = time.strftime("%H:%M:%S")
        data = json.dumps(
            {"type": log_type, "time": ts, "msg": msg}, ensure_ascii=False
        )
        with self._lock:
            dead = []
            for q in self._subscribers:
                try:
                    q.put_nowait(data)
                except Exception:
                    dead.append(q)
            for q in dead:
                self._subscribers.remove(q)


log_bus = LogBus()


# ──────────────────────────────────────────────
#  Config Manager
# ──────────────────────────────────────────────


class ConfigManager:
    def __init__(self):
        self._path = CONFIG_FILE
        self._config: dict = {}
        self._last_modified: float = 0

    def load(self) -> dict:
        with open(self._path, "r", encoding="utf-8") as f:
            self._config = json.load(f)

        for key in ("discord_client_id", "ai_api_key"):
            if not self._config.get(key):
                raise ValueError(f"config.json'da '{key}' alanını doldurun!")

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

    def save(self, updates: dict):
        with open(self._path, "r", encoding="utf-8") as f:
            full = json.load(f)

        safe_keys = {
            "ai_provider",
            "ai_api_key",
            "ai_model",
            "discord_client_id",
            "persona",
            "custom_persona_text",
            "language",
            "update_interval",
            "fallback_status",
            "show_button",
            "button_label",
            "button_url",
            "blacklist",
        }
        for k, v in updates.items():
            if k in safe_keys:
                full[k] = v

        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(full, f, indent=4, ensure_ascii=False)

        self._config = full
        self._last_modified = self._path.stat().st_mtime

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
#  Bot Engine Thread
# ──────────────────────────────────────────────


class BotEngine:
    """StatusAI bot engine running in a background thread."""

    def __init__(self, config_mgr: ConfigManager):
        self.config_mgr = config_mgr
        self._thread: threading.Thread | None = None
        self._running = False
        self._stop_event = threading.Event()
        self._current_status = ""
        self._start_time: float = 0
        self._rpc: DiscordRPC | None = None

    @property
    def running(self) -> bool:
        return self._running

    @property
    def current_status(self) -> str:
        return self._current_status

    @property
    def uptime(self) -> str:
        if not self._running or not self._start_time:
            return "00:00:00"
        elapsed = int(time.time() - self._start_time)
        h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    def start(self):
        if self._running:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        if not self._running:
            return
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._running = False

    def _log(self, log_type: str, msg: str):
        log_bus.emit(log_type, msg)

    def _run(self):
        self._running = True
        self._start_time = time.time()
        config = self.config_mgr.config
        tracked_apps = config.get("tracked_apps", {})
        blacklist = config.get("blacklist", [])
        interval = max(15, min(60, config.get("update_interval", 20)))

        # Connect to Discord
        self._log("info", "Discord RPC bağlanıyor...")
        try:
            self._rpc = DiscordRPC(config["discord_client_id"])
            self._rpc.connect()
            self._log("success", "Discord RPC bağlandı!")
        except Exception as e:
            self._log("error", f"RPC bağlantı hatası: {e}")
            self._running = False
            return

        self._log(
            "info",
            f"Bot başlatıldı! Güncelleme: {interval}s | Persona: {config.get('persona', 'custom').upper()}",
        )

        last_ctx = None
        cycle = 0

        while not self._stop_event.is_set():
            try:
                cycle += 1

                # Hot-reload config
                if cycle % 5 == 0 and self.config_mgr.check_reload():
                    config = self.config_mgr.config
                    tracked_apps = config.get("tracked_apps", {})
                    blacklist = config.get("blacklist", [])
                    interval = max(15, min(60, config.get("update_interval", 20)))
                    self._log("success", "🔄 Config yeniden yüklendi!")

                # 1. Context
                ctx = get_full_context(tracked_apps, blacklist)

                # 2. Check change
                if (
                    last_ctx is not None
                    and not ctx.has_changed(last_ctx)
                    and self._current_status
                ):
                    self._stop_event.wait(interval)
                    continue

                # 3. Build prompt
                context_prompt = ctx.build_prompt()
                self._log("info", f"Bağlam: {context_prompt}")

                if ctx.running_apps:
                    self._log("info", f"Çalışan: {', '.join(ctx.running_apps)}")

                # 4. Status generation
                if ctx.has_media:
                    new_status = ctx.build_direct_status()
                    if not new_status:
                        new_status = generate_status(context_prompt, config)
                else:
                    new_status = generate_status(context_prompt, config)

                if new_status != self._current_status:
                    self._current_status = new_status
                    self._log("status", f"→ {self._current_status}")

                    # Log to file
                    try:
                        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        with open(LOG_FILE, "a", encoding="utf-8") as f:
                            f.write(
                                f'[{ts}] {context_prompt} → "{self._current_status}"\n'
                            )
                    except Exception:
                        pass

                    # 5. Update Discord
                    try:
                        buttons = None
                        if config.get("show_button", False):
                            label = config.get("button_label", "⚡ StatusAI")
                            url = config.get("button_url", "")
                            if label and url:
                                buttons = [{"label": label, "url": url}]

                        details = None
                        if ctx.game_name:
                            details = ctx.game_name
                        elif ctx.active_app and ctx.active_app != "Unknown":
                            details = ctx.active_app

                        icon = "logo"
                        if ctx.game_name and ctx.game_name in APP_ICONS:
                            icon = APP_ICONS[ctx.game_name]
                        elif ctx.browser_platform and ctx.browser_platform in APP_ICONS:
                            icon = APP_ICONS[ctx.browser_platform]
                        elif ctx.active_app and ctx.active_app in APP_ICONS:
                            icon = APP_ICONS[ctx.active_app]

                        self._rpc.update(
                            state=self._current_status,
                            details=details,
                            large_image=icon,
                            large_text=ctx.active_app or "StatusAI",
                            small_image="logo",
                            small_text=f"StatusAI v{VERSION}",
                            buttons=buttons,
                        )
                        self._log("success", "Discord güncellendi!")
                    except Exception as e:
                        self._log("warn", f"RPC hatası: {e}")

                last_ctx = ctx
                self._stop_event.wait(interval)

            except Exception as e:
                self._log("error", f"Hata: {e}")
                self._stop_event.wait(interval)

        # Cleanup
        if self._rpc:
            try:
                self._rpc.close()
                self._log("info", "Discord RPC kapatıldı.")
            except Exception:
                pass
        self._running = False
        self._log("warn", "Bot durduruldu.")


# ──────────────────────────────────────────────
#  Flask App (Internal API Server)
# ──────────────────────────────────────────────

# Support for PyInstaller's extracted _MEIPASS folder containing templates
if getattr(sys, "frozen", False):
    template_folder = os.path.join(sys._MEIPASS, "templates")
    app = Flask(__name__, template_folder=template_folder, static_folder=None)
else:
    app = Flask(__name__)

app.config["SECRET_KEY"] = os.urandom(24).hex()

config_mgr = ConfigManager()
try:
    config_mgr.load()
except Exception as e:
    print(f"HATA: config.json yüklenemedi: {e}")
    sys.exit(1)

bot = BotEngine(config_mgr)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    stats = get_stats()
    return jsonify(
        {
            "running": bot.running,
            "current_status": bot.current_status,
            "uptime": bot.uptime,
            "ai_calls": stats.total_calls,
            "provider": config_mgr.config.get("ai_provider", "—"),
            "persona": config_mgr.config.get("persona", "—"),
        }
    )


@app.route("/api/toggle", methods=["POST"])
def api_toggle():
    data = request.get_json() or {}
    action = data.get("action", "toggle")

    if action == "start":
        if not bot.running:
            bot.start()
            return jsonify({"running": True, "message": "✅ Bot başlatıldı!"})
        return jsonify({"running": True, "message": "Bot zaten çalışıyor."})
    elif action == "stop":
        if bot.running:
            bot.stop()
            return jsonify({"running": False, "message": "⏹ Bot durduruldu."})
        return jsonify({"running": False, "message": "Bot zaten durmuş."})

    return jsonify({"running": bot.running, "message": "Bilinmeyen aksiyon."})


@app.route("/api/config", methods=["GET"])
def api_config_get():
    cfg = dict(config_mgr.config)
    if cfg.get("ai_api_key"):
        k = cfg["ai_api_key"]
        cfg["ai_api_key"] = k[:6] + "***" + k[-4:] if len(k) > 10 else "***"
    return jsonify(cfg)


@app.route("/api/config", methods=["POST"])
def api_config_save():
    updates = request.get_json() or {}

    if "ai_api_key" in updates and "***" in updates["ai_api_key"]:
        del updates["ai_api_key"]

    if "blacklist" in updates and isinstance(updates["blacklist"], str):
        # Convert comma separated string to list of stripped strings
        updates["blacklist"] = [
            x.strip() for x in updates["blacklist"].split(",") if x.strip()
        ]

    try:
        config_mgr.save(updates)
        return jsonify({"message": "✅ Config kaydedildi!"})
    except Exception as e:
        return jsonify({"message": f"Hata: {e}"}), 500


@app.route("/api/logs")
def api_logs():
    def stream():
        q = log_bus.subscribe()
        try:
            while True:
                try:
                    data = q.get(timeout=30)
                    yield f"data: {data}\n\n"
                except Empty:
                    yield f"data: {json.dumps({'type': 'ping', 'time': '', 'msg': ''})}\n\n"
        except GeneratorExit:
            log_bus.unsubscribe(q)

    return Response(
        stream(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/check_update", methods=["GET"])
def api_check_update():
    """
    Checks GitHub for the latest version.json and returns whether
    an update is available for the frontend to show a nag banner.
    """
    try:
        update_data = setup_updater.check_for_updates()
        return jsonify(update_data)
    except Exception as e:
        return jsonify({"update_available": False, "error": str(e)}), 500


@app.route("/api/performance", methods=["GET"])
def api_performance():
    """Returns basic system performance usage."""
    try:
        cpu_usage = psutil.cpu_percent(interval=None)

        # RAM usage in GB
        ram = psutil.virtual_memory()
        ram_gb = round(ram.used / (1024**3), 1)
        ram_total = round(ram.total / (1024**3), 1)

        return jsonify(
            {
                "cpu": cpu_usage,
                "ram_gb": ram_gb,
                "ram_total": ram_total,
                "ram_percent": ram.percent,
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ──────────────────────────────────────────────
#  System Tray
# ──────────────────────────────────────────────

_webview_window = None  # Reference to the native window


def _create_tray_icon_image():
    """Create or load system tray icon."""
    from PIL import Image, ImageDraw, ImageFont
    import os
    import sys

    try:
        # Check if we are running as a PyInstaller bundle
        base_path = (
            sys._MEIPASS
            if getattr(sys, "frozen", False)
            else os.path.abspath(os.path.dirname(__file__))
        )
        icon_path = os.path.join(base_path, "icon.ico")

        if not os.path.exists(icon_path):
            icon_path = os.path.join(base_path, "logo.jpg")

        if os.path.exists(icon_path):
            img = Image.open(icon_path)
            if img.mode != "RGBA":
                img = img.convert("RGBA")
            # 64x64 is a standard tray icon size
            return img.resize((64, 64), Image.Resampling.LANCZOS)
    except Exception as e:
        print(f"[Tray] Özel ikon yüklenemedi: {e}")

    # Fallback to drawn icon if missing
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, 60, 60], fill=(139, 92, 246, 255))
    try:
        font = ImageFont.truetype("arial.ttf", 32)
    except Exception:
        font = ImageFont.load_default()
    draw.text((20, 10), "S", fill=(255, 255, 255, 255), font=font)
    return img


def setup_tray():
    """Setup system tray icon with pystray."""
    import pystray

    def on_show(icon, item):
        """Show the native window."""
        if _webview_window:
            _webview_window.show()
            _webview_window.restore()

    def on_quit(icon, item):
        """Fully quit the application."""
        icon.stop()
        bot.stop()
        if _webview_window:
            _webview_window.destroy()
        os._exit(0)

    def on_bot_start(icon, item):
        bot.start()

    def on_bot_stop(icon, item):
        bot.stop()

    icon = pystray.Icon(
        "StatusAI",
        _create_tray_icon_image(),
        "StatusAI Dashboard",
        menu=pystray.Menu(
            pystray.MenuItem("🖥️ Pencereyi Göster", on_show, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Bot",
                pystray.Menu(
                    pystray.MenuItem("▶ Başlat", on_bot_start),
                    pystray.MenuItem("⏹ Durdur", on_bot_stop),
                ),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ Tamamen Kapat", on_quit),
        ),
    )
    return icon


# ──────────────────────────────────────────────
#  Window Close → Minimize to Tray
# ──────────────────────────────────────────────


def on_window_closing():
    """Called when user clicks X. Minimize to tray instead of quitting."""
    if _webview_window:
        _webview_window.hide()
    return False  # Prevent actual close


# ──────────────────────────────────────────────
#  Entry Point
# ──────────────────────────────────────────────


def main():
    global _webview_window

    import webview

    print(r"""
   _____ _        _              ___    _____
  / ____| |      | |            /   \  |_   _|
 | (___ | |_ __ _| |_ _   _ ___/ /_\ \   | |
  \___ \| __/ _` | __| | | / __\  _  |   | |
  ____) | || (_| | |_| |_| \__ \ | | |  _| |_
 |_____/ \__\__,_|\__|\__,_|___/_| |_| |_____|
                           Desktop App v3.0
    """)

    # ── 1. Start Flask API server in background thread ──
    flask_thread = threading.Thread(
        target=lambda: app.run(
            host="127.0.0.1", port=PORT, debug=False, use_reloader=False, threaded=True
        ),
        daemon=True,
    )
    flask_thread.start()
    time.sleep(0.5)  # Let Flask start

    # ── 2. Auto-start bot ──
    print("[StatusAI] Bot otomatik başlatılıyor...")
    bot.start()

    # ── 3. System tray (background thread) ──
    print("[StatusAI] Sistem tepsisi oluşturuluyor...")
    tray_icon = setup_tray()
    tray_thread = threading.Thread(target=tray_icon.run, daemon=True)
    tray_thread.start()

    # ── 4. Create native window (blocks main thread) ──
    print(f"[StatusAI] Uygulama penceresi açılıyor...")
    print(f"[StatusAI] Pencereyi kapatırsan bot arka planda çalışmaya devam eder.")
    print(f"[StatusAI] Tamamen kapatmak için: Sağ alt tray ikonu → Tamamen Kapat\n")

    _webview_window = webview.create_window(
        title="StatusAI — Dashboard",
        url=f"http://127.0.0.1:{PORT}",
        width=1100,
        height=750,
        min_size=(900, 600),
        background_color="#07070d",
        text_select=False,
        on_top=False,
    )

    # Hook the close event → minimize instead of quit
    _webview_window.events.closing += on_window_closing

    # Start the native window event loop (blocks here)
    webview.start(debug=False)

    # If webview exits normally (shouldn't happen with tray), cleanup
    bot.stop()
    tray_icon.stop()


if __name__ == "__main__":
    main()
