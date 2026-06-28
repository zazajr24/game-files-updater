#!/usr/bin/env python3
import os
import json
import glob
import re
from typing import Dict, List, Optional, Tuple


class ManifestFinder:
    def __init__(self, repo_root: str = None):
        if repo_root is None:
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.repo_root = repo_root
        self.manifests_dir = os.path.join(repo_root, "Manifests")
        self.cmds_path = os.path.join(repo_root, "cmds.json")
        self.games_path = os.path.join(repo_root, "games.json")
        self._cmds_cache = None
        self._games_cache = None
        self._dir_cache = None

    def _normalize(self, s: str) -> str:
        return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()

    def _resolve_manifest_folder(self, folder_rel: str) -> str:
        full = os.path.join(self.repo_root, folder_rel)
        if os.path.isdir(full):
            return full
        if self._dir_cache is None:
            if os.path.isdir(self.manifests_dir):
                self._dir_cache = {
                    self._normalize(d): os.path.join(self.manifests_dir, d)
                    for d in os.listdir(self.manifests_dir)
                    if os.path.isdir(os.path.join(self.manifests_dir, d))
                }
            else:
                self._dir_cache = {}
        parts = folder_rel.split("/")
        if len(parts) >= 2:
            target_norm = self._normalize(parts[-1])
            if target_norm in self._dir_cache:
                return self._dir_cache[target_norm]
            for norm_name, path in self._dir_cache.items():
                if target_norm in norm_name or norm_name in target_norm:
                    return path
            target_words = set(target_norm.split())
            best_score = 0
            best_path = full
            for norm_name, path in self._dir_cache.items():
                dir_words = set(norm_name.split())
                overlap = len(target_words & dir_words)
                score = overlap / max(len(target_words), len(dir_words), 1)
                if score > best_score and score > 0.6:
                    best_score = score
                    best_path = path
            if best_score > 0:
                return best_path
        return full

    def _load_cmds(self) -> Dict:
        if self._cmds_cache is None:
            with open(self.cmds_path, "r", encoding="utf-8") as f:
                self._cmds_cache = json.load(f)
        return self._cmds_cache

    def _load_games(self) -> List[Dict]:
        if self._games_cache is None:
            with open(self.games_path, "r", encoding="utf-8") as f:
                self._games_cache = json.load(f)
        return self._games_cache

    def parse_key_file(self, key_file_path: str) -> Dict[str, str]:
        keys = {}
        if not os.path.exists(key_file_path):
            return keys
        with open(key_file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if ";" in line:
                    depot_or_app, hex_key = line.split(";", 1)
                    keys[depot_or_app.strip()] = hex_key.strip()
        return keys

    def parse_lua_file(self, lua_path: str) -> List[Dict]:
        entries = []
        if not os.path.exists(lua_path):
            return entries
        with open(lua_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                match = re.match(
                    r'addappid\((\d+)(?:,\s*(\d+))?,?\s*"?([a-f0-9]*)"?\)',
                    line,
                )
                if match:
                    app_id = match.group(1)
                    flag = match.group(2) or "1"
                    key = match.group(3) or ""
                    comment = ""
                    if "--" in line:
                        comment = line.split("--", 1)[1].strip()
                    entries.append(
                        {
                            "app_id": app_id,
                            "flag": flag,
                            "key": key,
                            "comment": comment,
                        }
                    )
                elif line.startswith("addappid("):
                    match_no_key = re.match(r"addappid\((\d+)\)", line)
                    if match_no_key:
                        comment = ""
                        if "--" in line:
                            comment = line.split("--", 1)[1].strip()
                        entries.append(
                            {
                                "app_id": match_no_key.group(1),
                                "flag": "0",
                                "key": "",
                                "comment": comment,
                            }
                        )
        return entries

    def _auto_discover_game(self, folder_path: str) -> Optional[Dict]:
        key_files = [f for f in os.listdir(folder_path) if f.endswith(".key")]
        manifest_files = [f for f in os.listdir(folder_path) if f.endswith(".manifest")]
        lua_files = [f for f in os.listdir(folder_path) if f.endswith(".lua")]
        if not key_files:
            return None

        key_path = os.path.join(folder_path, key_files[0])
        depot_keys = self.parse_key_file(key_path)
        app_id = key_files[0].replace(".key", "")

        folder_name = os.path.basename(folder_path)
        name = folder_name.replace(" Manifests and Keys", "").replace("_", ": ").strip()

        lua_entries = []
        if lua_files:
            lua_path = os.path.join(folder_path, lua_files[0])
            lua_entries = self.parse_lua_file(lua_path)

        depots = []
        for mf in manifest_files:
            parts = mf.replace(".manifest", "").split("_", 1)
            if len(parts) == 2:
                depot_id, manifest_id = parts
                key = depot_keys.get(depot_id, "")
                label = "Base Game" if len(depots) == 0 else f"Pack {len(depots)}"
                depots.append({
                    "depot_id": depot_id,
                    "manifest_id": manifest_id,
                    "manifest_file": mf,
                    "manifest_path": os.path.join(folder_path, mf),
                    "label": label,
                    "key": key,
                    "has_manifest": True,
                })

        if not depots and lua_entries:
            for entry in lua_entries:
                if entry["key"]:
                    label = "Base Game" if len(depots) == 0 else f"Pack {len(depots)}"
                    depots.append({
                        "depot_id": entry["app_id"],
                        "manifest_id": "",
                        "manifest_file": "",
                        "manifest_path": "",
                        "label": entry.get("comment", label),
                        "key": entry["key"],
                        "has_manifest": False,
                    })

        return {
            "name": name,
            "app_id": app_id,
            "manifest_folder": folder_path,
            "key_file": key_path,
            "depot_keys": depot_keys,
            "depots": depots,
        }

    def get_all_games(self) -> Dict[str, Dict]:
        cmds = self._load_cmds()
        seen_apps = set()
        games = {}

        for game_name, game_data in cmds.items():
            if "depots" not in game_data:
                continue
            depots = game_data["depots"]
            if not depots:
                continue
            app_id = depots[0].get("app", "")
            if app_id in seen_apps:
                continue
            seen_apps.add(app_id)

            manifest_folder = game_data.get("manifest_folder", "")
            key_file = game_data.get("key_file", "")
            full_manifest_folder = self._resolve_manifest_folder(manifest_folder)
            full_key_path = os.path.join(full_manifest_folder, key_file) if key_file else ""

            depot_keys = {}
            if full_key_path and os.path.exists(full_key_path):
                depot_keys = self.parse_key_file(full_key_path)
            elif os.path.isdir(full_manifest_folder):
                for f in os.listdir(full_manifest_folder):
                    if f.endswith(".key"):
                        alt_key_path = os.path.join(full_manifest_folder, f)
                        depot_keys = self.parse_key_file(alt_key_path)
                        full_key_path = alt_key_path
                        break

            depot_list = []
            for depot in depots:
                depot_id = depot.get("depot", "")
                manifest_id = depot.get("manifest", "")
                mf_file = depot.get("mf", "")
                label = depot.get("label", "")
                key = depot_keys.get(depot_id, "")

                mf_full_path = os.path.join(full_manifest_folder, mf_file) if mf_file else ""
                has_manifest_file = os.path.exists(mf_full_path) if mf_full_path else False

                depot_list.append(
                    {
                        "depot_id": depot_id,
                        "manifest_id": manifest_id,
                        "manifest_file": mf_file,
                        "manifest_path": mf_full_path if has_manifest_file else "",
                        "label": label,
                        "key": key,
                        "has_manifest": has_manifest_file,
                    }
                )

            games[app_id] = {
                "name": game_data.get("game", game_name),
                "app_id": app_id,
                "manifest_folder": full_manifest_folder,
                "key_file": full_key_path,
                "depot_keys": depot_keys,
                "depots": depot_list,
            }

        if os.path.isdir(self.manifests_dir):
            for entry in os.listdir(self.manifests_dir):
                full = os.path.join(self.manifests_dir, entry)
                if not os.path.isdir(full):
                    continue
                if "Manifests and Keys" not in entry and "Manifest And Keys" not in entry:
                    continue
                discovered = self._auto_discover_game(full)
                if discovered and discovered["app_id"] not in seen_apps:
                    seen_apps.add(discovered["app_id"])
                    games[discovered["app_id"]] = discovered

        return games

    def get_game_by_appid(self, app_id: str) -> Optional[Dict]:
        games = self.get_all_games()
        return games.get(app_id)

    def search_games(self, query: str) -> List[Dict]:
        games = self.get_all_games()
        results = []
        query_lower = query.lower()
        for app_id, game in games.items():
            if query_lower in game["name"].lower() or query_lower == app_id:
                results.append(game)
        return results

    def get_all_manifest_files(self, app_id: str) -> List[str]:
        game = self.get_game_by_appid(app_id)
        if not game:
            return []
        manifest_folder = game["manifest_folder"]
        if not os.path.isdir(manifest_folder):
            return []
        manifests = []
        for f in os.listdir(manifest_folder):
            if f.endswith(".manifest"):
                manifests.append(f)
        return sorted(manifests)

    def get_game_size(self, app_id: str) -> Optional[float]:
        games_list = self._load_games()
        for g in games_list:
            if g.get("appid") == app_id:
                return g.get("size")
        return None

    def scan_manifest_dirs(self) -> List[Dict]:
        if not os.path.isdir(self.manifests_dir):
            return []
        results = []
        for entry in sorted(os.listdir(self.manifests_dir)):
            full = os.path.join(self.manifests_dir, entry)
            if os.path.isdir(full) and "Manifests and Keys" in entry:
                key_files = [f for f in os.listdir(full) if f.endswith(".key")]
                manifest_files = [f for f in os.listdir(full) if f.endswith(".manifest")]
                lua_files = [f for f in os.listdir(full) if f.endswith(".lua")]
                results.append(
                    {
                        "folder": entry,
                        "path": full,
                        "key_files": key_files,
                        "manifest_files": manifest_files,
                        "lua_files": lua_files,
                    }
                )
        return results


if __name__ == "__main__":
    finder = ManifestFinder()
    games = finder.get_all_games()
    print(f"Found {len(games)} games with manifest keys\n")
    for app_id, game in sorted(games.items(), key=lambda x: x[1]["name"]):
        n_depots = len(game["depots"])
        n_keys = len(game["depot_keys"])
        print(f"  [{app_id}] {game['name']} - {n_depots} depots, {n_keys} keys")
