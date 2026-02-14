import os
import json
import difflib
import subprocess
from pathlib import Path
import win32com.client


class WindowsAppIndexer:
    START_MENU_DIRS = [
        Path(os.environ["PROGRAMDATA"]) / "Microsoft/Windows/Start Menu/Programs",
        Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs",
    ]

    def __init__(
        self,
        app_cache_file="./cache/windows_app_cache.json",
        alias_file="./cache/windows_app_aliases.json",
    ):
        self.app_cache_file = app_cache_file
        self.alias_file = alias_file

        self.apps = {}      # canonical_name -> launch descriptor
        self.aliases = {}   # alias -> canonical_name
        self.build_cache()

    # ---------------- Public API ----------------

    def build_cache(self, force_rebuild=False):
        if os.path.exists(self.app_cache_file) and not force_rebuild:
            self._load_app_cache()
        else:
            self.apps = {}
            self._scan_start_menu_exes()
            self._scan_uwp_apps()
            self._save_app_cache()

        self._load_aliases()

    def search(self, query, min_score=0.6):
        query = self._normalize(query)

        # Alias resolution
        canonical = self._resolve_alias(query)
        if canonical and canonical in self.apps:
            return self.apps[canonical]

        # Fuzzy canonical match
        matches = difflib.get_close_matches(
            query,
            self.apps.keys(),
            n=1,
            cutoff=min_score
        )
        if matches:
            return self.apps[matches[0]]

        # Partial fallback
        for name, entry in self.apps.items():
            if query in name:
                return entry

        return None

    def launch(self, app_entry):
        if not app_entry:
            return False

        if app_entry["type"] == "exe":
            os.startfile(app_entry["path"])
            return True

        if app_entry["type"] == "uwp":
            subprocess.run([
                "explorer.exe",
                f"shell:AppsFolder\\{app_entry['aumid']}"
            ])
            return True

        return False

    def add_alias(self, alias, canonical_name):
        alias = self._normalize(alias)
        canonical_name = self._normalize(canonical_name)

        if canonical_name not in self.apps:
            raise ValueError(f"Unknown app: {canonical_name}")

        self.aliases[alias] = canonical_name
        self._save_aliases()

    # ---------------- Indexing ----------------

    def _scan_start_menu_exes(self):
        shell = win32com.client.Dispatch("WScript.Shell")

        for base_dir in self.START_MENU_DIRS:
            if not base_dir.exists():
                continue

            for lnk in base_dir.rglob("*.lnk"):
                try:
                    shortcut = shell.CreateShortcut(str(lnk))
                    target = shortcut.Targetpath

                    if target and target.lower().endswith(".exe") and os.path.exists(target):
                        name = self._normalize(lnk.stem)
                        self.apps[name] = {
                            "type": "exe",
                            "path": target
                        }
                except Exception:
                    continue

    def _scan_uwp_apps(self):
        """
        Uses PowerShell Get-StartApps to enumerate UWP / MSIX apps
        """
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-Command",
                    "Get-StartApps | ConvertTo-Json"
                ],
                capture_output=True,
                text=True,
                encoding="utf-8"
            )

            if not result.stdout.strip():
                return

            data = json.loads(result.stdout)

            # PowerShell returns dict if only one app exists
            if isinstance(data, dict):
                data = [data]

            for app in data:
                name = self._normalize(app["Name"])
                aumid = app["AppID"]

                if name not in self.apps:
                    self.apps[name] = {
                        "type": "uwp",
                        "aumid": aumid
                    }

        except Exception:
            pass

    # ---------------- Alias handling ----------------

    def _resolve_alias(self, query):
        if query in self.aliases:
            return self.aliases[query]

        matches = difflib.get_close_matches(
            query,
            self.aliases.keys(),
            n=1,
            cutoff=0.7
        )
        if matches:
            return self.aliases[matches[0]]

        return None

    # ---------------- Persistence ----------------

    def _normalize(self, text):
        return (
            text.lower()
            .replace("-", " ")
            .replace("_", " ")
            .strip()
        )

    def _save_app_cache(self):
        with open(self.app_cache_file, "w", encoding="utf-8") as f:
            json.dump(self.apps, f, indent=2)

    def _load_app_cache(self):
        with open(self.app_cache_file, "r", encoding="utf-8") as f:
            self.apps = json.load(f)

    def _save_aliases(self):
        with open(self.alias_file, "w", encoding="utf-8") as f:
            json.dump(self.aliases, f, indent=2)

    def _load_aliases(self):
        if os.path.exists(self.alias_file):
            with open(self.alias_file, "r", encoding="utf-8") as f:
                self.aliases = json.load(f)
        else:
            self.aliases = {}
