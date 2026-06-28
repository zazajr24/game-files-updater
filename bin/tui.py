#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Steam Spoofer TUI - Terminal User Interface

import os
import sys

IS_WINDOWS = sys.platform == "win32"

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    import pyfiglet
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from spoofer import Spoofer


class SpooferTUI:
    def __init__(self):
        self.spoofer = Spoofer()
        self.running = True
        self.use_rich = RICH_AVAILABLE
        if self.use_rich:
            self.console = Console()

    def run(self):
        self._clear()
        self._banner()
        while self.running:
            try:
                self._menu()
                cmd = input("\n[SPOOF] > ").strip()
                self._handle(cmd)
            except KeyboardInterrupt:
                self.running = False
                print("\n[EXIT] Goodbye!")
            except EOFError:
                self.running = False
            except Exception as e:
                print(f"[ERROR] {e}")

    def _clear(self):
        os.system("cls" if IS_WINDOWS else "clear")

    def _banner(self):
        total = len(self.spoofer.games)
        platform = "Windows" if IS_WINDOWS else "Linux"
        if self.use_rich:
            try:
                banner = pyfiglet.figlet_format("SPOOFER", font="slant")
                self.console.print(f"[red]{banner}[/red]")
            except Exception:
                self.console.print("[bold red]STEAM SPOOFER[/bold red]")
            self.console.print("[red]" + "=" * 60 + "[/red]")
            self.console.print(
                f"[bold red]STEAM MANIFEST KEY SPOOFER[/bold red]"
            )
            self.console.print(
                f"[red]Platform: {platform} | Games: {total} | Real Keys[/red]"
            )
            self.console.print("[red]" + "=" * 60 + "[/red]")
        else:
            print("+" + "=" * 50 + "+")
            print("|    STEAM MANIFEST KEY SPOOFER                    |")
            print(f"|    Platform: {platform:<10} | Games: {total:<5}          |")
            print("|    Real .key files | Backwards Compatible        |")
            print("+" + "=" * 50 + "+")

    def _menu(self):
        if self.use_rich:
            table = Table(title="Commands", box=box.ROUNDED)
            table.add_column("Key", style="green", width=18)
            table.add_column("Action", style="white")
            table.add_row("L", "List all games with keys")
            table.add_row("S <app_id>", "Spoof a game")
            table.add_row("R <app_id>", "Restore a game")
            table.add_row("D <app_id>", "Show download commands")
            table.add_row("K <app_id>", "Show depot keys")
            table.add_row("E <app_id>", "Export game files (.key, .lua)")
            table.add_row("V <app_id>", "Show version history")
            table.add_row("G", "List spoofed games")
            table.add_row("I <app_id>", "Game info")
            table.add_row("F <keyword>", "Search games")
            table.add_row("B <app_id>", "Generate batch download script")
            table.add_row("A", "Spoof ALL games")
            table.add_row("C", "Clear console")
            table.add_row("X", "Exit")
            self.console.print(table)
            spoofed = len(self.spoofer.list_spoofed())
            total = len(self.spoofer.games)
            self.console.print(
                f"[dim]Spoofed: {spoofed} | Total: {total}[/dim]"
            )
        else:
            print("\n=== COMMANDS ===")
            print("  L              - List all games with keys")
            print("  S <app_id>     - Spoof a game")
            print("  R <app_id>     - Restore a game")
            print("  D <app_id>     - Show download commands")
            print("  K <app_id>     - Show depot keys")
            print("  E <app_id>     - Export game files (.key, .lua)")
            print("  V <app_id>     - Show version history")
            print("  G              - List spoofed games")
            print("  I <app_id>     - Game info")
            print("  F <keyword>    - Search games")
            print("  B <app_id>     - Generate batch download script")
            print("  A              - Spoof ALL games")
            print("  C              - Clear console")
            print("  X              - Exit")

    def _handle(self, cmd: str):
        parts = cmd.split(None, 1)
        if not parts:
            return
        action = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else ""

        if action == "l":
            self._list_games()
        elif action == "s":
            if arg:
                self.spoofer.spoof(arg)
            else:
                print("[ERROR] Usage: S <app_id>")
        elif action == "r":
            if arg:
                self.spoofer.restore(arg)
            else:
                print("[ERROR] Usage: R <app_id>")
        elif action == "d":
            if arg:
                self._show_download_commands(arg)
            else:
                print("[ERROR] Usage: D <app_id>")
        elif action == "k":
            if arg:
                self._show_keys(arg)
            else:
                print("[ERROR] Usage: K <app_id>")
        elif action == "e":
            if arg:
                self._export_game(arg)
            else:
                print("[ERROR] Usage: E <app_id>")
        elif action == "v":
            if arg:
                self._show_versions(arg)
            else:
                print("[ERROR] Usage: V <app_id>")
        elif action == "g":
            self._list_spoofed()
        elif action == "i":
            if arg:
                self._show_info(arg)
            else:
                print("[ERROR] Usage: I <app_id>")
        elif action == "f":
            if arg:
                self._search(arg)
            else:
                print("[ERROR] Usage: F <keyword>")
        elif action == "b":
            if arg:
                self._generate_batch(arg)
            else:
                print("[ERROR] Usage: B <app_id>")
        elif action == "a":
            self._spoof_all()
        elif action == "c":
            self._clear()
            self._banner()
        elif action in ("x", "exit", "quit"):
            self.running = False
            print("\n[EXIT] Spoofer terminated")
        elif action == "help":
            self._menu()
        else:
            print(f"[ERROR] Unknown command: {action}")

    def _list_games(self):
        games = self.spoofer.list_games()
        if self.use_rich:
            table = Table(
                title=f"Available Games ({len(games)})", box=box.ROUNDED
            )
            table.add_column("App ID", style="cyan", width=10)
            table.add_column("Name", style="white", width=45)
            table.add_column("Depots", style="yellow", justify="right", width=7)
            table.add_column("Keys", style="green", justify="right", width=6)
            table.add_column("Spoofed", style="magenta", justify="center", width=8)
            for app_id, data in sorted(
                games.items(), key=lambda x: x[1]["name"]
            ):
                spoofed = "[green]YES[/green]" if self.spoofer.db.is_spoofed(app_id) else "[dim]no[/dim]"
                table.add_row(
                    app_id,
                    data["name"],
                    str(len(data["depots"])),
                    str(len(data["depot_keys"])),
                    spoofed,
                )
            self.console.print(table)
        else:
            print(f"\n=== AVAILABLE GAMES ({len(games)}) ===")
            for app_id, data in sorted(
                games.items(), key=lambda x: x[1]["name"]
            ):
                spoofed = " [SPOOFED]" if self.spoofer.db.is_spoofed(app_id) else ""
                n_depots = len(data["depots"])
                n_keys = len(data["depot_keys"])
                print(
                    f"  {app_id:>10}: {data['name']:<45} "
                    f"({n_depots} depots, {n_keys} keys){spoofed}"
                )

    def _show_download_commands(self, app_id: str):
        cmds = self.spoofer.get_download_commands(app_id)
        if not cmds:
            print(f"[ERROR] No commands for: {app_id}")
            return
        game = self.spoofer.games.get(app_id, {})
        name = game.get("name", app_id)
        if self.use_rich:
            self.console.print(
                Panel(f"[bold]{name}[/bold] (AppID: {app_id})", title="Download Commands")
            )
            for cmd in cmds:
                self.console.print(
                    f"\n[yellow][{cmd['label']}][/yellow] Depot {cmd['depot_id']}"
                )
                self.console.print(f"  Manifest: {cmd['manifest_id']}")
                if cmd["key"]:
                    self.console.print(f"  Key: [green]{cmd['key'][:32]}...[/green]")
                self.console.print(f"  [dim]{cmd['command_str']}[/dim]")
        else:
            print(f"\n=== Download Commands: {name} ===")
            for cmd in cmds:
                print(f"\n  [{cmd['label']}] Depot {cmd['depot_id']}")
                print(f"  Manifest: {cmd['manifest_id']}")
                if cmd["key"]:
                    print(f"  Key: {cmd['key'][:32]}...")
                print(f"  CMD: {cmd['command_str']}")

    def _show_keys(self, app_id: str):
        game = self.spoofer.games.get(app_id)
        if not game:
            print(f"[ERROR] Game not found: {app_id}")
            return
        name = game["name"]
        depot_keys = game["depot_keys"]
        if self.use_rich:
            table = Table(
                title=f"Depot Keys: {name}", box=box.ROUNDED
            )
            table.add_column("Depot/App ID", style="cyan")
            table.add_column("Key (hex)", style="green")
            for did, key in sorted(depot_keys.items()):
                table.add_row(did, key)
            self.console.print(table)
        else:
            print(f"\n=== Depot Keys: {name} ===")
            for did, key in sorted(depot_keys.items()):
                print(f"  {did}: {key}")
        print(f"\nTotal keys: {len(depot_keys)}")

    def _export_game(self, app_id: str):
        output = self.spoofer.downloader.export_game_manifest(app_id)
        if output:
            print(f"[SUCCESS] Exported to: {output}")
        else:
            print(f"[ERROR] Could not export: {app_id}")

    def _show_versions(self, app_id: str):
        versions = self.spoofer.get_game_versions(app_id)
        if not versions:
            game = self.spoofer.games.get(app_id)
            if game:
                print(f"\n[INFO] Current version for {game['name']}:")
                for depot in game["depots"]:
                    print(
                        f"  Depot {depot['depot_id']}: manifest {depot['manifest_id']} ({depot['label']})"
                    )
                print("\n[INFO] No version history yet. Spoof the game first to start tracking.")
            else:
                print(f"[ERROR] Game not found: {app_id}")
            return

        if self.use_rich:
            table = Table(title="Version History", box=box.ROUNDED)
            table.add_column("Date", style="yellow")
            table.add_column("Depot", style="cyan")
            table.add_column("Manifest", style="white")
            table.add_column("Label", style="green")
            for v in versions:
                table.add_row(
                    v["captured_date"][:19],
                    v["depot_id"],
                    v["manifest_id"],
                    v["label"],
                )
            self.console.print(table)
        else:
            print(f"\n=== Version History: {app_id} ===")
            for v in versions:
                print(
                    f"  {v['captured_date'][:19]} | "
                    f"Depot {v['depot_id']} | "
                    f"Manifest {v['manifest_id']} | "
                    f"{v['label']}"
                )

    def _list_spoofed(self):
        spoofed = self.spoofer.list_spoofed()
        if not spoofed:
            print("\n[INFO] No games spoofed yet")
            return

        if self.use_rich:
            table = Table(title="Spoofed Games", box=box.ROUNDED)
            table.add_column("App ID", style="cyan")
            table.add_column("Name", style="white")
            table.add_column("Date", style="yellow")
            table.add_column("Depots", style="green", justify="right")
            table.add_column("Keys", style="magenta", justify="right")
            for game in spoofed:
                table.add_row(
                    game["app_id"],
                    game["name"],
                    game["spoof_date"][:16],
                    str(game.get("depot_count", 0)),
                    str(game.get("key_count", 0)),
                )
            self.console.print(table)
        else:
            print(f"\n=== SPOOFED GAMES ({len(spoofed)}) ===")
            for game in spoofed:
                print(
                    f"  {game['app_id']}: {game['name']} "
                    f"({game['spoof_date'][:16]}) "
                    f"[{game.get('depot_count', 0)} depots, {game.get('key_count', 0)} keys]"
                )

    def _show_info(self, app_id: str):
        info = self.spoofer.get_game_info(app_id)
        if not info:
            print(f"[ERROR] Game not found: {app_id}")
            return

        if self.use_rich:
            table = Table(
                title=f"Game Info: {info['name']}", box=box.ROUNDED
            )
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="white")
            table.add_row("App ID", info["app_id"])
            table.add_row("Name", info["name"])
            table.add_row("Depots", str(len(info["depots"])))
            table.add_row("Keys", str(len(info["depot_keys"])))
            if info.get("size_gb"):
                table.add_row("Size", f"{info['size_gb']} GB")
            table.add_row("Spoofed", "Yes" if info["spoofed"] else "No")
            table.add_row("Spoof Count", str(info["spoof_count"]))
            self.console.print(table)

            if info["depots"]:
                depot_table = Table(title="Depots", box=box.SIMPLE)
                depot_table.add_column("Depot ID", style="cyan")
                depot_table.add_column("Manifest ID", style="white")
                depot_table.add_column("Label", style="yellow")
                depot_table.add_column("Key", style="green")
                depot_table.add_column("MF File", style="dim")
                for d in info["depots"]:
                    key_display = d["key"][:24] + "..." if d["key"] else "[dim]none[/dim]"
                    has_mf = "[green]YES[/green]" if d["has_manifest"] else "[dim]no[/dim]"
                    depot_table.add_row(
                        d["depot_id"],
                        d["manifest_id"],
                        d["label"],
                        key_display,
                        has_mf,
                    )
                self.console.print(depot_table)
        else:
            print(f"\n=== {info['name']} ===")
            print(f"  App ID:     {info['app_id']}")
            print(f"  Depots:     {len(info['depots'])}")
            print(f"  Keys:       {len(info['depot_keys'])}")
            if info.get("size_gb"):
                print(f"  Size:       {info['size_gb']} GB")
            print(f"  Spoofed:    {'Yes' if info['spoofed'] else 'No'}")
            print(f"  Spoof Count: {info['spoof_count']}")
            print("\n  Depots:")
            for d in info["depots"]:
                key_short = d["key"][:24] + "..." if d["key"] else "none"
                print(
                    f"    {d['depot_id']}: {d['label']} | "
                    f"manifest={d['manifest_id']} | key={key_short}"
                )

    def _search(self, query: str):
        results = self.spoofer.search_games(query)
        if not results:
            print(f"[INFO] No games found for: {query}")
            return

        if self.use_rich:
            table = Table(
                title=f"Search: '{query}' ({len(results)} results)", box=box.ROUNDED
            )
            table.add_column("App ID", style="cyan")
            table.add_column("Name", style="white")
            table.add_column("Depots", style="yellow", justify="right")
            table.add_column("Keys", style="green", justify="right")
            for game in results:
                table.add_row(
                    game["app_id"],
                    game["name"],
                    str(len(game["depots"])),
                    str(len(game["depot_keys"])),
                )
            self.console.print(table)
        else:
            print(f"\n=== Search: '{query}' ({len(results)} results) ===")
            for game in results:
                print(
                    f"  {game['app_id']}: {game['name']} "
                    f"({len(game['depots'])} depots, {len(game['depot_keys'])} keys)"
                )

    def _generate_batch(self, app_id: str):
        path = self.spoofer.downloader.generate_batch_script(app_id)
        if path:
            print(f"[SUCCESS] Script generated: {path}")
        else:
            print(f"[ERROR] Could not generate script for: {app_id}")

    def _spoof_all(self):
        games = self.spoofer.list_games()
        total = len(games)
        print(f"\n[INFO] Spoofing all {total} games...")
        success = 0
        for i, (app_id, game) in enumerate(
            sorted(games.items(), key=lambda x: x[1]["name"]), 1
        ):
            print(f"\n[{i}/{total}] {game['name']}")
            if self.spoofer.spoof(app_id):
                success += 1
        print(f"\n[DONE] Spoofed {success}/{total} games")


def main():
    print("Initializing Steam Manifest Key Spoofer...")
    tui = SpooferTUI()
    tui.run()


if __name__ == "__main__":
    main()
