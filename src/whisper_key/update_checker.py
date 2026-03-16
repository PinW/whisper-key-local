import json
import subprocess
import sys
import urllib.request
import urllib.error

from .terminal_ui import prompt_choice
from .utils import get_version

PYPI_URL = "https://pypi.org/pypi/whisper-key-local/json"
PYPI_TIMEOUT = 3

UPDATE_NOW = 1
ALWAYS_UPDATE = 2
NOT_NOW = 3


def fetch_latest_version():
    try:
        req = urllib.request.Request(PYPI_URL)
        with urllib.request.urlopen(req, timeout=PYPI_TIMEOUT) as response:
            data = json.loads(response.read())
            return data["info"]["version"]
    except Exception:
        return None


def is_newer(latest, current):
    try:
        from packaging.version import Version
        return Version(latest) > Version(current)
    except Exception:
        return False


def check_for_updates(config_manager, test_mode=False):
    version = get_version()
    is_dev = version.endswith("-dev") or test_mode

    latest = fetch_latest_version()
    compare_version = version.replace("-dev", "") if version.endswith("-dev") else version
    if not latest or not is_newer(latest, compare_version):
        return

    if is_dev:
        print(f"   ** Update available: {version} -> {latest} (git pull to update)")
        return

    update_config = config_manager.get_update_config()

    if update_config.get('mode') == 'auto':
        run_update()
        return

    choice = prompt_choice("Update available: {} -> {}".format(version, latest), [
        ("Update now", "Downloads and installs the update"),
        ("Always keep up-to-date", "Update now and auto-install future updates"),
        ("Not now", "Skip for this session"),
    ])

    if choice == UPDATE_NOW:
        run_update()
    elif choice == ALWAYS_UPDATE:
        config_manager.update_user_setting('update', 'mode', 'auto')
        run_update()


def run_update():
    print("   Updating...")
    result = subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "whisper-key-local"])
    if result.returncode != 0:
        print("   Update failed. Please try again later.")
        return
    print("   Update installed. Please restart Whisper Key.")
    sys.exit(0)
