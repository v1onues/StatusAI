import urllib.request
import json
import os

# GitHub repo raw URL for version.json
GITHUB_RAW_URL = "https://raw.githubusercontent.com/v1onues/StatusAI/main/version.json"


def get_current_version():
    """Reads the current version from local version.json"""
    version_file = "version.json"

    # If packaged with PyInstaller, use the correct base path
    if hasattr(os, "sys") and getattr(os.sys, "frozen", False):
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = getattr(
                os.sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))
            )
            version_file = os.path.join(base_path, "version.json")
        except Exception:
            pass

    try:
        if os.path.exists(version_file):
            with open(version_file, "r") as f:
                data = json.load(f)
                return data.get("version", "3.0.0")
    except Exception as e:
        print(f"[Updater] Error reading local version.json: {e}")

    return "3.0.0"


def check_for_updates():
    """Fetches the latest version.json from GitHub and compares it with local version."""
    current_ver = get_current_version()

    result = {
        "update_available": False,
        "current_version": current_ver,
        "latest_version": current_ver,
        "release_url": "https://github.com/v1onues/StatusAI/releases",
    }

    try:
        req = urllib.request.Request(
            GITHUB_RAW_URL, headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.getcode() == 200:
                data = json.loads(response.read().decode("utf-8"))
                latest_ver = data.get("version", current_ver)

                result["latest_version"] = latest_ver
                result["release_url"] = data.get("release_url", result["release_url"])

                # Simple version string comparison (assuming semantic versioning X.Y.Z)
                # This could be more sophisticated using packaging.version if necessary,
                # but direct string comparison or splitting by '.' assumes basic format.
                if current_ver != latest_ver:
                    c_parts = [int(p) for p in current_ver.split(".") if p.isdigit()]
                    l_parts = [int(p) for p in latest_ver.split(".") if p.isdigit()]

                    if l_parts > c_parts:
                        result["update_available"] = True

    except Exception as e:
        print(f"[Updater] Failed to check for updates: {e}")

    return result


if __name__ == "__main__":
    print(check_for_updates())
