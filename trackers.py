"""
trackers.py — StatusAI Multi-Source Activity Tracker v3
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Uses Win32 API (ctypes) for window detection and psutil for process enumeration.
Now with: multi-source context, Spotify detection, browser platform detection,
VS Code file/project extraction, and privacy filtering.
"""

import ctypes
import ctypes.wintypes
import re
from dataclasses import dataclass, field
from typing import Optional

import psutil


# ──────────────────────────────────────────────
#  Data Models
# ──────────────────────────────────────────────

@dataclass
class FullContext:
    """
    Multi-source activity context.
    Captures everything the user is doing simultaneously.
    """
    # Active window
    active_app: str = ""
    active_title: str = ""
    process_name: str = ""

    # VS Code
    vscode_file: str = ""
    vscode_project: str = ""

    # Spotify
    spotify_track: str = ""
    spotify_artist: str = ""

    # Browser
    browser_platform: str = ""       # GitHub, StackOverflow, YouTube, etc.
    browser_page_title: str = ""

    # Game
    game_name: str = ""

    # Running apps (filtered, friendly names)
    running_apps: list[str] = field(default_factory=list)

    # Privacy-filtered messaging
    is_messaging: bool = False

    def build_prompt(self) -> str:
        """Build a structured, detailed prompt string for the Storyteller AI."""
        lines: list[str] = []

        # Game takes priority
        if self.game_name:
            return f"OYUN: {self.game_name} oynuyor"

        # Active app (always include)
        if self.active_app and self.active_app != "Unknown":
            if self.active_title and not self.is_messaging:
                lines.append(f"AKTİF: {self.active_app} — {self.active_title[:80]}")
            elif self.is_messaging:
                lines.append(f"AKTİF: Mesajlaşma uygulamasında iletişim kuruyor")
            else:
                lines.append(f"AKTİF: {self.active_app}")

        # VS Code detail
        if self.vscode_file:
            proj = f" ({self.vscode_project} projesi)" if self.vscode_project else ""
            lines.append(f"KOD: VS Code'da {self.vscode_file} dosyasını düzenliyor{proj}")

        # Spotify detail
        if self.spotify_track:
            artist = f" ({self.spotify_artist})" if self.spotify_artist else ""
            lines.append(f"MÜZİK: {self.spotify_track}{artist} dinliyor")

        # Browser platform + YouTube detection
        if self.browser_platform:
            if self.browser_page_title:
                lines.append(f"TARAYICI: {self.browser_platform}'da — {self.browser_page_title}")
            else:
                lines.append(f"TARAYICI: {self.browser_platform}'da geziniyor")

        # Fallback
        if not lines:
            return "Bilgisayar başında"

        return "\n".join(lines)

    @property
    def has_media(self) -> bool:
        """Check if there's YouTube video or Spotify track."""
        return bool(self.spotify_track or
                    (self.browser_platform and self.browser_platform == "YouTube" and self.browser_page_title))

    def build_direct_status(self) -> str:
        """
        Build a template-based status with LITERAL video/song names.
        No AI involved — video and song titles are shown exactly as-is.
        Returns empty string if no media context (caller should use AI instead).
        """
        # Game takes priority
        if self.game_name:
            return f"{self.game_name} oynuyor 🎮"

        media_part = ""
        activity_part = ""

        # ── Media: YouTube ──
        yt_title = ""
        if self.browser_platform == "YouTube" and self.browser_page_title:
            # Clean YouTube title (remove " - YouTube" if still there)
            yt_title = self.browser_page_title
            for suffix in (" - YouTube", " — YouTube"):
                if yt_title.endswith(suffix):
                    yt_title = yt_title[:-len(suffix)].strip()
            # Truncate long titles
            if len(yt_title) > 50:
                yt_title = yt_title[:47] + "..."
            media_part = f'YouTube\'da "{yt_title}" izliyor 🎵'

        # ── Media: Spotify (takes priority over YouTube if both exist) ──
        if self.spotify_track:
            track = self.spotify_track
            if len(track) > 40:
                track = track[:37] + "..."
            if self.spotify_artist:
                artist = self.spotify_artist
                if len(artist) > 20:
                    artist = artist[:17] + "..."
                media_part = f'{artist} - "{track}" dinliyor 🎧'
            else:
                media_part = f'"{track}" dinliyor 🎧'

        if not media_part:
            return ""  # No media — caller should use AI

        # ── Activity prefix ──
        if self.vscode_file:
            proj = f" ({self.vscode_project})" if self.vscode_project else ""
            activity_part = f"{self.vscode_file}{proj} düzenlerken"
        elif self.is_messaging:
            activity_part = "Sohbet ederken"
        elif self.active_app and self.active_app not in ("Unknown", "Chrome", "explorer"):
            if self.active_app == "Discord":
                activity_part = "Discord'da takılırken"
            else:
                activity_part = f"{self.active_app} kullanırken"

        # ── Combine ──
        if activity_part:
            status = f"{activity_part} {media_part}"
        else:
            status = media_part

        # Enforce 128 char limit
        if len(status) > 128:
            status = status[:125] + "..."

        return status

    def has_changed(self, other: "FullContext") -> bool:
        """Check if context has meaningfully changed."""
        if other is None:
            return True
        return (
            self.active_app != other.active_app
            or self.active_title != other.active_title
            or self.vscode_file != other.vscode_file
            or self.spotify_track != other.spotify_track
            or self.browser_platform != other.browser_platform
            or self.game_name != other.game_name
            or self.is_messaging != other.is_messaging
        )


# ──────────────────────────────────────────────
#  Known Games
# ──────────────────────────────────────────────

KNOWN_GAMES: dict[str, str] = {
    "League of Legends.exe": "League of Legends",
    "LeagueClient.exe": "League of Legends",
    "VALORANT.exe": "VALORANT",
    "VALORANT-Win64-Shipping.exe": "VALORANT",
    "csgo.exe": "CS:GO",
    "cs2.exe": "CS2",
    "GTA5.exe": "GTA V",
    "RocketLeague.exe": "Rocket League",
    "FortniteClient-Win64-Shipping.exe": "Fortnite",
    "r5apex.exe": "Apex Legends",
    "minecraft.exe": "Minecraft",
    "javaw.exe": "Minecraft",
    "Overwatch.exe": "Overwatch 2",
    "RainbowSix.exe": "Rainbow Six Siege",
    "EscapeFromTarkov.exe": "Escape from Tarkov",
    "PUBG-Win64-Shipping.exe": "PUBG",
    "dota2.exe": "Dota 2",
}


# ──────────────────────────────────────────────
#  Privacy: Messaging Apps
# ──────────────────────────────────────────────

MESSAGING_APPS = {
    "whatsapp.exe", "telegram.exe", "signal.exe",
    "slack.exe", "teams.exe", "skype.exe",
    "messenger.exe", "viber.exe",
}


# ──────────────────────────────────────────────
#  Browser Platform Detection
# ──────────────────────────────────────────────

BROWSER_PROCESSES = {
    "chrome.exe", "firefox.exe", "msedge.exe", "brave.exe",
    "opera.exe", "supermium.exe", "vivaldi.exe", "chromium.exe",
}

BROWSER_SUFFIXES = (
    " - Google Chrome", " - Mozilla Firefox", " - Microsoft Edge",
    " — Mozilla Firefox", " - Brave", " - Opera", " - Supermium",
    " - Chromium",
)

PLATFORM_PATTERNS: list[tuple[str, str]] = [
    (r"github\.com|github", "GitHub"),
    (r"stackoverflow\.com|stack overflow", "StackOverflow"),
    (r"reddit\.com|reddit", "Reddit"),
    (r"youtube\.com|youtu\.be|youtube", "YouTube"),
    (r"twitter\.com|x\.com", "X/Twitter"),
    (r"linkedin\.com|linkedin", "LinkedIn"),
    (r"medium\.com", "Medium"),
    (r"dev\.to", "Dev.to"),
    (r"npmjs\.com|npm", "npm"),
    (r"pypi\.org", "PyPI"),
    (r"docs\.python\.org", "Python Docs"),
    (r"developer\.mozilla\.org|mdn", "MDN"),
    (r"vercel\.com", "Vercel"),
    (r"netlify\.com", "Netlify"),
    (r"docker\.com|docker hub", "Docker Hub"),
    (r"aws\.amazon\.com", "AWS"),
    (r"cloud\.google\.com", "Google Cloud"),
    (r"azure\.microsoft\.com", "Azure"),
    (r"figma\.com|figma", "Figma"),
    (r"notion\.so|notion", "Notion"),
    (r"trello\.com|trello", "Trello"),
    (r"chatgpt\.com|openai\.com|chatgpt", "ChatGPT"),
    (r"gemini\.google\.com", "Gemini"),
    (r"claude\.ai", "Claude"),
    (r"discord\.com", "Discord Web"),
    (r"twitch\.tv|twitch", "Twitch"),
    (r"spotify\.com", "Spotify Web"),
]

# ──────────────────────────────────────────────
#  NSFW / Adult Filters
# ──────────────────────────────────────────────

NSFW_PATTERNS: list[str] = [
    r"pornhub\.com", r"xvideos\.com", r"xnxx\.com", r"xhamster\.com",
    r"onlyfans\.com", r"rule34", r"nhentai", r"e621", r"gelbooru",
    r"hanime", r"hentai", r"porn", r"sex", r"chaturbate", r"stripchat"
]


# ──────────────────────────────────────────────
#  Win32 Helpers
# ──────────────────────────────────────────────

def _get_foreground_window_info() -> tuple[str, str]:
    """Returns (window_title, process_name) of the foreground window."""
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]

        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return "", ""

        # Window title
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        window_title = buf.value

        # Process name
        pid = ctypes.wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

        process_name = ""
        try:
            proc = psutil.Process(pid.value)
            process_name = proc.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

        return window_title, process_name

    except Exception:
        return "", ""


def _find_process_window_title(target_process: str) -> str:
    """Find window title for a specific process (e.g. Spotify)."""
    try:
        for proc in psutil.process_iter(["name", "pid"]):
            try:
                if proc.info["name"] and proc.info["name"].lower() == target_process.lower():
                    return _get_window_title_by_pid(proc.info["pid"])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        pass
    return ""


def _get_window_title_by_pid(pid: int) -> str:
    """Get window title for a specific process ID."""
    try:
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]

        result = {"title": ""}

        @ctypes.WINFUNCTYPE(ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
        def enum_callback(hwnd, lparam):
            window_pid = ctypes.wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
            if window_pid.value == pid and user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    if buf.value and len(buf.value) > 3:
                        result["title"] = buf.value
                        return False  # Stop enumeration
            return True

        user32.EnumWindows(enum_callback, 0)
        return result["title"]

    except Exception:
        return ""


# ──────────────────────────────────────────────
#  Smart Extractors
# ──────────────────────────────────────────────

def _extract_vscode(title: str) -> tuple[str, str]:
    """Extract file and project from VS Code title."""
    # Format: "filename.ext — ProjectName — Visual Studio Code"
    # or: "filename.ext — Visual Studio Code"
    parts = title.split(" — ")
    if len(parts) >= 3:
        return parts[0].strip(), parts[1].strip()
    elif len(parts) == 2:
        return parts[0].strip(), ""
    return "", ""


def _extract_spotify(title: str) -> tuple[str, str]:
    """Extract track and artist from Spotify title."""
    # Format: "Song - Artist" or "Spotify Premium"
    if not title or title.lower().startswith("spotify"):
        return "", ""
    if " - " in title:
        parts = title.split(" - ", 1)
        return parts[0].strip(), parts[1].strip()
    return title.strip(), ""


def _extract_browser_platform(title: str) -> tuple[str, str]:
    """Detect platform and clean title from browser window."""
    # Remove browser suffix
    clean_title = title
    for suffix in BROWSER_SUFFIXES:
        if suffix in clean_title:
            clean_title = clean_title.split(suffix)[0].strip()
            break

    title_lower = clean_title.lower()

    # 1. Check NSFW Patterns FIRST
    for pattern in NSFW_PATTERNS:
        if re.search(pattern, title_lower):
            return "Gizli", ""  # Suppress completely

    # 2. Detect platform
    for pattern, platform_name in PLATFORM_PATTERNS:
        if re.search(pattern, title_lower):
            # Also strip platform name suffix from page title
            page_title = clean_title
            platform_lower = platform_name.lower()
            # Remove trailing " - YouTube", " - GitHub", etc.
            for sep in (" - ", " — ", " | "):
                parts = page_title.rsplit(sep, 1)
                if len(parts) == 2 and parts[1].strip().lower() in (
                    platform_lower, platform_lower.replace(" ", ""),
                    "youtube", "github", "reddit", "stackoverflow",
                    "twitch", "linkedin", "figma", "notion", "trello",
                ):
                    page_title = parts[0].strip()
                    break
            return platform_name, page_title[:80]

    # Unknown site
    if clean_title and len(clean_title) > 3:
        return "", clean_title[:60]
    return "", ""


def _is_process_running(name: str) -> bool:
    """Check if a process is currently running."""
    name_lower = name.lower()
    try:
        for proc in psutil.process_iter(["name"]):
            try:
                if proc.info["name"] and proc.info["name"].lower() == name_lower:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        pass
    return False


# ──────────────────────────────────────────────
#  Public API
# ──────────────────────────────────────────────

def get_full_context(tracked_apps: dict[str, str], blacklist: list[str] = None) -> FullContext:
    """
    Gather multi-source context from the system.
    Returns a FullContext with all simultaneous activities.
    """
    ctx = FullContext()
    
    if blacklist is None:
        blacklist = []

    # ── 1. Active foreground window ──
    window_title, process_name = _get_foreground_window_info()
    proc_lower = process_name.lower() if process_name else ""

    # Check for games
    if proc_lower in BROWSER_PROCESSES:
        platform_name, page_title = _extract_browser_platform(window_title) # Changed to _extract_browser_platform
        
        # Check Backlist Words
        page_title_lower = page_title.lower() if page_title else ""
        for word in blacklist:
            if word.lower() in page_title_lower:
                platform_name = "Gizli"
                page_title = ""
                break
                
        ctx.browser_platform = platform_name
        ctx.browser_page_title = page_title # Changed to browser_page_title
        ctx.active_app = platform_name or "Tarayıcı"
        ctx.active_title = page_title # Corrected typo
    else: # Added else block for non-browser processes
        if process_name in KNOWN_GAMES: # Original game check moved here
            ctx.game_name = KNOWN_GAMES[process_name]
            ctx.active_app = ctx.game_name
            ctx.process_name = process_name
            ctx.running_apps = _get_running_apps(tracked_apps)
            return ctx

        # Friendly name
        friendly = tracked_apps.get(process_name, "")
        if not friendly:
            for key, value in tracked_apps.items():
                if key.lower() == proc_lower:
                    friendly = value
                    break
        if not friendly:
            friendly = process_name.replace(".exe", "") if process_name else "Unknown"

        is_blacklisted = False
        title_lower = window_title.lower() if window_title else ""
        for word in blacklist:
            if word.lower() in title_lower:
                is_blacklisted = True
                break
                
        if is_blacklisted:
            ctx.active_title = ""
            ctx.active_app = "Gizli"
        else:
            ctx.active_app = friendly # Changed mapped_name to friendly
            ctx.active_title = window_title
            
        ctx.process_name = process_name

    # ── 2. Privacy check: messaging apps ──
    if proc_lower in MESSAGING_APPS:
        ctx.is_messaging = True
        ctx.active_title = ""  # Scrub title for privacy

    # ── 3. VS Code detection ──
    if proc_lower == "code.exe":
        ctx.vscode_file, ctx.vscode_project = _extract_vscode(window_title)
    elif _is_process_running("Code.exe"):
        # VS Code is running but not in foreground
        vscode_title = _find_process_window_title("Code.exe")
        if vscode_title:
            ctx.vscode_file, ctx.vscode_project = _extract_vscode(vscode_title)

    # ── 4. Spotify detection (background) ──
    spotify_title = _find_process_window_title("Spotify.exe")
    if spotify_title:
        ctx.spotify_track, ctx.spotify_artist = _extract_spotify(spotify_title)

    # ── 5. Browser platform detection ──
    # Check if active app is a browser (by process name OR tracked_apps name)
    is_browser = (proc_lower in BROWSER_PROCESSES
                  or friendly.lower() in ("chrome", "firefox", "edge", "brave", "opera", "supermium", "vivaldi"))
    if is_browser:
        ctx.browser_platform, ctx.browser_page_title = _extract_browser_platform(window_title)
    elif not ctx.is_messaging:
        # Check if a browser is running in background
        for browser in BROWSER_PROCESSES:
            if _is_process_running(browser):
                browser_title = _find_process_window_title(browser)
                if browser_title:
                    ctx.browser_platform, ctx.browser_page_title = _extract_browser_platform(browser_title)
                    break

    # ── 6. Running apps ──
    ctx.running_apps = _get_running_apps(tracked_apps)

    return ctx


def _get_running_apps(tracked_apps: dict[str, str]) -> list[str]:
    """Returns friendly names of running tracked applications."""
    running: set[str] = set()
    tracked_lower = {k.lower(): v for k, v in tracked_apps.items()}

    try:
        for proc in psutil.process_iter(["name"]):
            try:
                name = proc.info["name"]  # type: ignore[index]
                if name and name.lower() in tracked_lower:
                    running.add(tracked_lower[name.lower()])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        pass

    return sorted(running)
