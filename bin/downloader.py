#!/usr/bin/env python3
import os
import sys
import json
import subprocess
import platform
from typing import Dict, List, Optional
from datetime import datetime

from manifest_finder import ManifestFinder


class DepotDownloaderCmd:
    def __init__(self, repo_root: str = None):
        self.finder = ManifestFinder(repo_root)
        self.repo_root = self.finder.repo_root
        self.games_dir = os.path.join(self.repo_root, "games")
        os.makedirs(self.games_dir, exist_ok=True)

    def build_download_commands(
        self,
        app_id: str,
        output_dir: str = None,
        depot_ids: List[str] = None,
        use_manifest_file: bool = True,
    ) -> List[Dict]:
        game = self.finder.get_game_by_appid(app_id)
        if not game:
            return []

        if output_dir is None:
            output_dir = os.path.join(self.games_dir, app_id)

        commands = []
        for depot in game["depots"]:
            if depot_ids and depot["depot_id"] not in depot_ids:
                continue

            cmd_parts = [
                "dotnet",
                "DepotDownloader.dll",
                "-app", app_id,
                "-depot", depot["depot_id"],
                "-manifest", depot["manifest_id"],
            ]

            if depot["key"]:
                cmd_parts.extend(["-depotkey", depot["key"]])

            if use_manifest_file and depot["has_manifest"] and depot["manifest_path"]:
                cmd_parts.extend(["-manifestfile", depot["manifest_path"]])

            cmd_parts.extend(["-dir", output_dir])

            commands.append(
                {
                    "app_id": app_id,
                    "depot_id": depot["depot_id"],
                    "manifest_id": depot["manifest_id"],
                    "label": depot["label"],
                    "key": depot["key"],
                    "command": cmd_parts,
                    "command_str": " ".join(cmd_parts),
                    "output_dir": output_dir,
                }
            )

        return commands

    def build_key_file_content(self, app_id: str) -> str:
        game = self.finder.get_game_by_appid(app_id)
        if not game:
            return ""
        lines = []
        for depot in game["depots"]:
            if depot["key"]:
                lines.append(f"{depot['depot_id']};{depot['key']}")
        if game["depot_keys"]:
            for did, key in game["depot_keys"].items():
                entry = f"{did};{key}"
                if entry not in lines:
                    lines.append(entry)
        return "\n".join(lines)

    def build_lua_content(self, app_id: str) -> str:
        game = self.finder.get_game_by_appid(app_id)
        if not game:
            return ""
        lines = [
            f"-- {app_id}'s Lua and Manifest",
            f"-- {game['name']}",
            f"-- Generated: {datetime.now().strftime('%B %d, %Y at %H:%M:%S')}",
            f"-- Total Depots: {len(game['depots'])}",
            "",
            "-- MAIN APPLICATION",
        ]
        app_key = game["depot_keys"].get(app_id, "")
        if app_key:
            lines.append(f'addappid({app_id}, 1, "{app_key}") -- {game["name"]}')
        else:
            lines.append(f"addappid({app_id}) -- {game['name']}")
        lines.append("-- DEPOTS")
        for depot in game["depots"]:
            if depot["key"]:
                lines.append(
                    f'addappid({depot["depot_id"]}, 1, "{depot["key"]}") -- {depot["label"]}'
                )
            else:
                lines.append(f'addappid({depot["depot_id"]}) -- {depot["label"]}')
        return "\n".join(lines)

    def export_game_manifest(self, app_id: str, output_dir: str = None) -> str:
        game = self.finder.get_game_by_appid(app_id)
        if not game:
            return ""

        if output_dir is None:
            output_dir = os.path.join(self.games_dir, app_id)
        os.makedirs(output_dir, exist_ok=True)

        key_content = self.build_key_file_content(app_id)
        key_path = os.path.join(output_dir, f"{app_id}.key")
        with open(key_path, "w", encoding="utf-8") as f:
            f.write(key_content)

        lua_content = self.build_lua_content(app_id)
        lua_path = os.path.join(output_dir, f"{app_id}.lua")
        with open(lua_path, "w", encoding="utf-8") as f:
            f.write(lua_content)

        manifest_json = {
            "app_id": app_id,
            "name": game["name"],
            "exported": datetime.now().isoformat(),
            "depots": [],
        }
        for depot in game["depots"]:
            manifest_json["depots"].append(
                {
                    "depot_id": depot["depot_id"],
                    "manifest_id": depot["manifest_id"],
                    "label": depot["label"],
                    "has_key": bool(depot["key"]),
                    "has_manifest_file": depot["has_manifest"],
                }
            )
        manifest_path = os.path.join(output_dir, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_json, f, indent=2)

        return output_dir

    def generate_batch_script(
        self, app_id: str, output_path: str = None
    ) -> str:
        game = self.finder.get_game_by_appid(app_id)
        if not game:
            return ""

        commands = self.build_download_commands(app_id)
        if not commands:
            return ""

        is_windows = platform.system() == "Windows"

        if output_path is None:
            ext = ".bat" if is_windows else ".sh"
            output_path = os.path.join(
                self.games_dir, app_id, f"download_{app_id}{ext}"
            )
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if is_windows:
            lines = [
                "@echo off",
                f"REM Download script for {game['name']} (AppID: {app_id})",
                f"REM Generated: {datetime.now().isoformat()}",
                f"REM Depots: {len(commands)}",
                "",
            ]
            for cmd in commands:
                lines.append(f"echo Downloading {cmd['label']} (Depot {cmd['depot_id']})...")
                lines.append(cmd["command_str"])
                lines.append("")
            lines.append("echo Download complete!")
            lines.append("pause")
        else:
            lines = [
                "#!/bin/bash",
                f"# Download script for {game['name']} (AppID: {app_id})",
                f"# Generated: {datetime.now().isoformat()}",
                f"# Depots: {len(commands)}",
                "",
                'set -e',
                "",
            ]
            for cmd in commands:
                lines.append(f"echo 'Downloading {cmd['label']} (Depot {cmd['depot_id']})...'")
                lines.append(cmd["command_str"])
                lines.append("")
            lines.append("echo 'Download complete!'")

        content = "\n".join(lines)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        if not is_windows:
            os.chmod(output_path, 0o755)

        return output_path


if __name__ == "__main__":
    dl = DepotDownloaderCmd()
    if len(sys.argv) > 1:
        app_id = sys.argv[1]
        game = dl.finder.get_game_by_appid(app_id)
        if game:
            print(f"\nGame: {game['name']} (AppID: {app_id})")
            print(f"Depots: {len(game['depots'])}")
            print(f"Keys: {len(game['depot_keys'])}")
            print("\nDownload commands:")
            for cmd in dl.build_download_commands(app_id):
                print(f"\n  [{cmd['label']}] Depot {cmd['depot_id']}")
                print(f"  {cmd['command_str']}")
        else:
            print(f"Game not found: {app_id}")
    else:
        print("Usage: python downloader.py <app_id>")
        print("\nAvailable games:")
        for app_id, game in sorted(
            dl.finder.get_all_games().items(), key=lambda x: x[1]["name"]
        ):
            print(f"  {app_id}: {game['name']}")
