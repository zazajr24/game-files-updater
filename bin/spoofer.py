#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# STEAM SPOOFER - MANIFEST KEY EDITION
# Reads real .key files and manifests from the repo
# Windows + Linux - Backwards compatible version downloads

import os
import sys
import json
import sqlite3
import hashlib
import time
import shutil
from datetime import datetime
from typing import Dict, List, Optional

IS_WINDOWS = sys.platform == "win32"
IS_LINUX = sys.platform.startswith("linux")

if IS_WINDOWS:
    try:
        import winreg
        WIN32_AVAILABLE = True
    except ImportError:
        WIN32_AVAILABLE = False
else:
    WIN32_AVAILABLE = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, SCRIPT_DIR)

from manifest_finder import ManifestFinder
from downloader import DepotDownloaderCmd


def get_paths():
    if IS_WINDOWS:
        home = os.environ.get("USERPROFILE", "C:/Users/Default")
        return {
            "data": f"{home}/AppData/Local/SteamSpoofer",
            "db": f"{home}/AppData/Local/SteamSpoofer/spoofer.db",
            "steam": "C:/Program Files (x86)/Steam",
            "temp": f"{home}/AppData/Local/Temp/SteamSpoofer",
            "games": os.path.join(REPO_ROOT, "games"),
            "logs": os.path.join(REPO_ROOT, "logs"),
        }
    else:
        home = os.environ.get("HOME", "/home/user")
        return {
            "data": f"{home}/.steam_spoofer",
            "db": f"{home}/.steam_spoofer/spoofer.db",
            "steam": f"{home}/.steam",
            "temp": "/tmp/steam_spoofer",
            "games": os.path.join(REPO_ROOT, "games"),
            "logs": os.path.join(REPO_ROOT, "logs"),
        }


PATHS = get_paths()
os.makedirs(PATHS["data"], exist_ok=True)
os.makedirs(PATHS["games"], exist_ok=True)
os.makedirs(PATHS["logs"], exist_ok=True)


class SpoofDB:
    def __init__(self):
        self.db_path = PATHS["db"]
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS spoofed_games (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                app_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                spoof_date TEXT NOT NULL,
                method TEXT,
                manifest_id TEXT,
                depot_count INTEGER DEFAULT 0,
                key_count INTEGER DEFAULT 0,
                success INTEGER DEFAULT 1,
                restored INTEGER DEFAULT 0
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS manifest_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id TEXT NOT NULL,
                depot_id TEXT NOT NULL,
                manifest_id TEXT NOT NULL,
                key_hex TEXT,
                captured_date TEXT NOT NULL,
                label TEXT
            )
        """)
        conn.commit()
        conn.close()

    def add_spoofed(self, app_id: str, name: str, method: str, manifest_id: str = "",
                    depot_count: int = 0, key_count: int = 0) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("""
                INSERT OR REPLACE INTO spoofed_games
                (id, name, app_id, platform, spoof_date, method, manifest_id,
                 depot_count, key_count, success)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"{app_id}_{int(time.time())}",
                name, app_id,
                "windows" if IS_WINDOWS else "linux",
                datetime.now().isoformat(),
                method, manifest_id,
                depot_count, key_count, 1,
            ))
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    def add_manifest_history(self, app_id: str, depot_id: str, manifest_id: str,
                             key_hex: str = "", label: str = "") -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("""
                INSERT INTO manifest_history
                (app_id, depot_id, manifest_id, key_hex, captured_date, label)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (app_id, depot_id, manifest_id, key_hex,
                  datetime.now().isoformat(), label))
            conn.commit()
            conn.close()
            return True
        except Exception:
            return False

    def get_manifest_history(self, app_id: str) -> List[Dict]:
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute(
                "SELECT * FROM manifest_history WHERE app_id = ? ORDER BY captured_date DESC",
                (app_id,),
            )
            rows = c.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception:
            return []

    def get_spoofed_games(self) -> List[Dict]:
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute("SELECT * FROM spoofed_games ORDER BY spoof_date DESC")
            rows = c.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception:
            return []

    def is_spoofed(self, app_id: str) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(
                "SELECT COUNT(*) FROM spoofed_games WHERE app_id = ? AND success = 1",
                (app_id,),
            )
            count = c.fetchone()[0]
            conn.close()
            return count > 0
        except Exception:
            return False

    def get_spoof_count(self, app_id: str) -> int:
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute(
                "SELECT COUNT(*) FROM spoofed_games WHERE app_id = ?",
                (app_id,),
            )
            count = c.fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0


class Spoofer:
    def __init__(self):
        self.db = SpoofDB()
        self.finder = ManifestFinder(REPO_ROOT)
        self.downloader = DepotDownloaderCmd(REPO_ROOT)
        self._games_cache = None

    @property
    def games(self) -> Dict:
        if self._games_cache is None:
            self._games_cache = self.finder.get_all_games()
        return self._games_cache

    def spoof(self, app_id: str) -> bool:
        game = self.games.get(app_id)
        if not game:
            print(f"[ERROR] Unknown game: {app_id}")
            return False

        name = game["name"]
        n_depots = len(game["depots"])
        n_keys = len(game["depot_keys"])

        print(f"\n[SPOOFING] {name} (AppID: {app_id})")
        print(f"[INFO] Depots: {n_depots} | Keys: {n_keys}")

        success = False
        if IS_WINDOWS:
            success = self._spoof_windows(app_id, name, game)
        elif IS_LINUX:
            success = self._spoof_linux(app_id, name, game)

        if success:
            for depot in game["depots"]:
                self.db.add_manifest_history(
                    app_id, depot["depot_id"], depot["manifest_id"],
                    depot["key"], depot["label"],
                )
            self.db.add_spoofed(
                app_id, name, "manifest_key",
                game["depots"][0]["manifest_id"] if game["depots"] else "",
                n_depots, n_keys,
            )
            self._export_game_files(app_id, game)
            print(f"[SUCCESS] {name} spoofed with {n_keys} manifest keys!")
            return True

        print(f"[FAILED] Could not spoof {name}")
        return False

    def _export_game_files(self, app_id: str, game: Dict):
        output_dir = os.path.join(PATHS["games"], app_id)
        os.makedirs(output_dir, exist_ok=True)

        self.downloader.export_game_manifest(app_id, output_dir)
        self.downloader.generate_batch_script(app_id)

        for depot in game["depots"]:
            if depot["has_manifest"] and depot["manifest_path"]:
                src = depot["manifest_path"]
                dst = os.path.join(output_dir, os.path.basename(src))
                if os.path.exists(src) and not os.path.exists(dst):
                    shutil.copy2(src, dst)

        print(f"  [+] Game files exported to {output_dir}")

    def _spoof_windows(self, app_id: str, name: str, game: Dict) -> bool:
        methods = []

        if self._registry_spoof(app_id, name, game):
            methods.append("registry")
        if self._config_spoof(app_id, name):
            methods.append("config")
        if self._manifest_spoof(app_id, game):
            methods.append("manifest")
        if self._acf_spoof(app_id, name, game):
            methods.append("acf")

        return len(methods) > 0

    def _registry_spoof(self, app_id: str, name: str, game: Dict) -> bool:
        if not WIN32_AVAILABLE:
            return False
        try:
            key_path = f"Software\\Valve\\Steam\\Apps\\{app_id}"
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
            winreg.SetValueEx(key, "Name", 0, winreg.REG_SZ, name)
            winreg.SetValueEx(key, "Installed", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "Running", 0, winreg.REG_DWORD, 0)
            winreg.SetValueEx(key, "SpoofDate", 0, winreg.REG_SZ, datetime.now().isoformat())
            n_keys = len(game["depot_keys"])
            winreg.SetValueEx(key, "ManifestKeys", 0, winreg.REG_DWORD, n_keys)
            winreg.CloseKey(key)
            print("  [+] Registry spoof applied")
            return True
        except Exception:
            return False

    def _config_spoof(self, app_id: str, name: str) -> bool:
        try:
            config_path = os.path.join(PATHS["steam"], "config", "config.vdf")
            if not os.path.exists(config_path):
                return False
            with open(config_path, "r", encoding="utf-8") as f:
                content = f.read()
            if f'"{app_id}"' in content:
                print("  [~] Config entry already exists")
                return True
            with open(config_path, "a", encoding="utf-8") as f:
                f.write(f'\n"{app_id}"\n{{\n')
                f.write(f'    "name" "{name}"\n')
                f.write(f'    "installdir" "{PATHS["data"]}/Games/{name}"\n')
                f.write(f'    "SizeOnDisk" "0"\n')
                f.write(f'    "StateFlags" "4"\n')
                f.write(f'}}\n')
            print("  [+] Config spoof applied")
            return True
        except Exception:
            return False

    def _manifest_spoof(self, app_id: str, game: Dict) -> bool:
        try:
            manifest_dir = os.path.join(PATHS["data"], "manifests")
            os.makedirs(manifest_dir, exist_ok=True)

            manifest_data = {
                "appid": app_id,
                "name": game["name"],
                "spoofed": True,
                "date": datetime.now().isoformat(),
                "platform": "windows" if IS_WINDOWS else "linux",
                "depots": [],
            }
            for depot in game["depots"]:
                manifest_data["depots"].append({
                    "depot_id": depot["depot_id"],
                    "manifest_id": depot["manifest_id"],
                    "label": depot["label"],
                    "key": depot["key"],
                    "has_manifest_file": depot["has_manifest"],
                })

            manifest_file = os.path.join(manifest_dir, f"{app_id}.manifest.json")
            with open(manifest_file, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=2)

            key_content = self.downloader.build_key_file_content(app_id)
            if key_content:
                key_file = os.path.join(manifest_dir, f"{app_id}.key")
                with open(key_file, "w", encoding="utf-8") as f:
                    f.write(key_content)

            print(f"  [+] Manifest spoof applied ({len(game['depots'])} depots)")
            return True
        except Exception:
            return False

    def _acf_spoof(self, app_id: str, name: str, game: Dict) -> bool:
        try:
            steamapps = os.path.join(PATHS["steam"], "steamapps")
            if not os.path.isdir(steamapps):
                return False

            acf_path = os.path.join(steamapps, f"appmanifest_{app_id}.acf")
            safe_name = name.replace('"', '\\"')
            acf_content = f'''"AppState"
{{
    "appid"     "{app_id}"
    "Universe"      "1"
    "name"      "{safe_name}"
    "StateFlags"        "4"
    "installdir"        "{safe_name}"
    "SizeOnDisk"        "0"
    "buildid"       "0"
    "LastOwner"     "0"
    "BytesToDownload"       "0"
    "BytesDownloaded"       "0"
    "AutoUpdateBehavior"        "0"
    "InstalledDepots"
    {{
'''
            for depot in game["depots"]:
                acf_content += f'        "{depot["depot_id"]}"\n'
                acf_content += f'        {{\n'
                acf_content += f'            "manifest"      "{depot["manifest_id"]}"\n'
                acf_content += f'            "size"      "0"\n'
                acf_content += f'        }}\n'

            acf_content += '    }\n}\n'

            with open(acf_path, "w", encoding="utf-8") as f:
                f.write(acf_content)
            print("  [+] ACF manifest spoof applied")
            return True
        except Exception:
            return False

    def _spoof_linux(self, app_id: str, name: str, game: Dict) -> bool:
        methods = []

        if self._config_spoof(app_id, name):
            methods.append("config")
        if self._manifest_spoof(app_id, game):
            methods.append("manifest")
        if self._acf_spoof(app_id, name, game):
            methods.append("acf")

        return len(methods) > 0

    def restore(self, app_id: str) -> bool:
        game = self.games.get(app_id)
        if not game:
            print(f"[ERROR] Unknown game: {app_id}")
            return False

        name = game["name"]
        print(f"\n[RESTORING] {name}")

        if IS_WINDOWS and WIN32_AVAILABLE:
            try:
                key_path = f"Software\\Valve\\Steam\\Apps\\{app_id}"
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
            except Exception:
                pass

        config_path = os.path.join(PATHS["steam"], "config", "config.vdf")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                new_lines = []
                skip = False
                for line in lines:
                    if f'"{app_id}"' in line:
                        skip = True
                    elif skip and line.strip() == "}":
                        skip = False
                        continue
                    if not skip:
                        new_lines.append(line)
                with open(config_path, "w", encoding="utf-8") as f:
                    f.writelines(new_lines)
            except Exception:
                pass

        acf_path = os.path.join(PATHS["steam"], "steamapps", f"appmanifest_{app_id}.acf")
        if os.path.exists(acf_path):
            os.remove(acf_path)

        manifest_json = os.path.join(PATHS["data"], "manifests", f"{app_id}.manifest.json")
        if os.path.exists(manifest_json):
            os.remove(manifest_json)

        print(f"  [+] {name} restored")
        return True

    def get_download_commands(self, app_id: str) -> List[Dict]:
        return self.downloader.build_download_commands(app_id)

    def get_game_versions(self, app_id: str) -> List[Dict]:
        return self.db.get_manifest_history(app_id)

    def list_games(self) -> Dict:
        return self.games

    def list_spoofed(self) -> List[Dict]:
        return self.db.get_spoofed_games()

    def search_games(self, query: str) -> List[Dict]:
        return self.finder.search_games(query)

    def get_game_info(self, app_id: str) -> Optional[Dict]:
        game = self.games.get(app_id)
        if not game:
            return None
        size = self.finder.get_game_size(app_id)
        return {
            **game,
            "spoofed": self.db.is_spoofed(app_id),
            "spoof_count": self.db.get_spoof_count(app_id),
            "size_gb": size,
            "versions": self.db.get_manifest_history(app_id),
        }


if __name__ == "__main__":
    spoofer = Spoofer()
    print(f"Loaded {len(spoofer.games)} games with manifest keys")
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "list":
            for app_id, game in sorted(spoofer.games.items(), key=lambda x: x[1]["name"]):
                print(f"  [{app_id}] {game['name']} ({len(game['depots'])} depots)")
        elif cmd == "spoof" and len(sys.argv) > 2:
            spoofer.spoof(sys.argv[2])
        elif cmd == "restore" and len(sys.argv) > 2:
            spoofer.restore(sys.argv[2])
        elif cmd == "info" and len(sys.argv) > 2:
            info = spoofer.get_game_info(sys.argv[2])
            if info:
                print(json.dumps(info, indent=2, default=str))
        elif cmd == "commands" and len(sys.argv) > 2:
            cmds = spoofer.get_download_commands(sys.argv[2])
            for c in cmds:
                print(f"\n[{c['label']}] {c['command_str']}")
    else:
        print("Usage: python spoofer.py <list|spoof|restore|info|commands> [app_id]")
