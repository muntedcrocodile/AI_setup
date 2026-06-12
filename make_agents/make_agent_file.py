#!/usr/bin/env python3
import logging
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"

if VENV_PYTHON.exists():
    venv_python = str(VENV_PYTHON)
    if sys.executable != venv_python:
        os.execv(venv_python, [venv_python, __file__] + sys.argv[1:])

import curses
import json
from typing import Any

import click

from input_popup import input_popup
from template_creator import run_opencode_interactive
from tree_builder import Tree, load_templates

SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = SCRIPT_DIR / "agents_templates"
CONFIG_FILE = SCRIPT_DIR / "template_config.json"

logger = logging.getLogger(__name__)

DEFAULT_CONFIG: dict[str, Any] = {
    "templates": {},
    "ui_state": {"expanded_paths": []},
}


def load_config() -> dict[str, Any]:
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
        if "templates" not in data:
            data["templates"] = {}
        if "ui_state" not in data:
            data["ui_state"] = {"expanded_paths": []}
        if "expanded_paths" not in data["ui_state"]:
            data["ui_state"]["expanded_paths"] = []
        return data
    return json.loads(json.dumps(DEFAULT_CONFIG))


def save_config(config: dict[str, Any]) -> None:
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")


def draw_header(stdscr, target_dir: str) -> None:
    h, w = stdscr.getmaxyx()
    title = f" Select templates for {target_dir} "
    try:
        stdscr.addstr(0, 0, title.ljust(w)[:w], curses.A_REVERSE)
    except curses.error:
        pass


def draw_footer(stdscr) -> None:
    h, w = stdscr.getmaxyx()
    msg = " Space: toggle | ←/→: collapse/expand | ^R: refresh | ^S: save | ^A: add | Enter: confirm | Esc: quit "
    try:
        stdscr.addstr(h - 1, 0, msg.ljust(w)[:w], curses.A_DIM)
    except curses.error:
        pass


def show_message(stdscr, msg: str, delay_ms: int = 1000) -> None:
    h, w = stdscr.getmaxyx()
    try:
        stdscr.addstr(h - 2, 0, msg.ljust(w)[:w], curses.A_BOLD)
        stdscr.refresh()
    except curses.error:
        pass
    curses.napms(delay_ms)


def adjust_scroll(cursor_idx: int, scroll: int, visible_count: int, viewport_h: int) -> int:
    max_visible = viewport_h - 3
    if max_visible <= 0:
        return 0
    if cursor_idx < scroll:
        return cursor_idx
    if cursor_idx >= scroll + max_visible:
        return cursor_idx - max_visible + 1
    return max(0, scroll)


def main(stdscr, target_dir: str):
    try:
        curses.cbreak()
        curses.noecho()
        stdscr.keypad(True)
        curses.curs_set(0)
    except curses.error as exc:
        raise RuntimeError(
            "Could not initialise the terminal UI. "
            "make_agent_file.py must be run from an interactive terminal "
            "(a TTY is required for curses). "
            f"Underlying error: {exc}"
        ) from exc

    templates = load_templates(TEMPLATES_DIR)
    if not templates:
        stdscr.clear()
        try:
            stdscr.addstr(0, 0, "No templates found in agents_templates/")
        except curses.error:
            pass
        stdscr.getch()
        return None

    config = load_config()
    selected = {name: bool(config["templates"].get(name, False)) for name in templates}
    tree = Tree(templates)
    tree.apply_expansion_state(config["ui_state"].get("expanded_paths", []))

    visible = tree.visible_nodes()
    cursor_idx = 0
    scroll = 0

    def persist() -> None:
        config["templates"] = {n: bool(selected.get(n, False)) for n in templates}
        config["ui_state"]["expanded_paths"] = tree.expanded_paths()
        save_config(config)

    def rebuild() -> None:
        nonlocal tree, visible, cursor_idx, scroll
        tree = Tree(templates)
        tree.apply_expansion_state(config["ui_state"].get("expanded_paths", []))
        visible = tree.visible_nodes()
        cursor_idx = 0
        scroll = 0

    def refresh() -> int:
        """Re-read the template files from disk and rebuild the tree.

        Preserves the current cursor by path if that node still exists;
        otherwise falls back to the top of the list. Returns the number
        of templates now loaded so the caller can show a status message.
        """
        nonlocal templates, selected, tree, visible, cursor_idx, scroll
        prior_path = visible[cursor_idx].path if visible and 0 <= cursor_idx < len(visible) else ""
        templates = load_templates(TEMPLATES_DIR)
        selected = {name: bool(selected.get(name, False)) for name in templates}
        tree = Tree(templates)
        tree.apply_expansion_state(config["ui_state"].get("expanded_paths", []))
        visible = tree.visible_nodes()
        if prior_path:
            for idx, node in enumerate(visible):
                if node.path == prior_path:
                    cursor_idx = idx
                    break
            else:
                cursor_idx = 0
        else:
            cursor_idx = 0
        scroll = 0
        return len(templates)

    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()
        draw_header(stdscr, target_dir)
        scroll = adjust_scroll(cursor_idx, scroll, len(visible), h)

        body_start_y = 1
        if scroll > 0:
            try:
                stdscr.addstr(
                    body_start_y,
                    0,
                    f"  … {scroll} hidden above".ljust(w)[:w],
                    curses.A_DIM,
                )
            except curses.error:
                pass
            body_start_y += 1

        for offset, node in enumerate(visible[scroll:]):
            y = body_start_y + offset
            if y >= h - 1:
                break
            node.render_self(
                stdscr,
                y=y,
                depth=node.path.count("/"),
                width=w,
                selected=selected,
                is_cursor=(scroll + offset == cursor_idx),
            )
        draw_footer(stdscr)
        stdscr.refresh()

        key = stdscr.getch()

        if not visible:
            continue

        if key == 27:
            persist()
            return None
        if key == ord("\n"):
            persist()
            break
        if key == ord(" "):
            visible[cursor_idx].toggle_selection(selected)
            persist()
        elif key in (curses.KEY_RIGHT, ord("l")):
            if visible[cursor_idx].expand():
                visible = tree.visible_nodes()
                persist()
        elif key in (curses.KEY_LEFT, ord("h")):
            if visible[cursor_idx].collapse():
                visible = tree.visible_nodes()
                persist()
        elif key == curses.KEY_UP:
            if cursor_idx > 0:
                cursor_idx -= 1
        elif key == curses.KEY_DOWN:
            if cursor_idx < len(visible) - 1:
                cursor_idx += 1
        elif key == 19:
            persist()
            show_message(stdscr, "Defaults saved!")
        elif key == 18:
            count = refresh()
            persist()
            show_message(stdscr, f"Refreshed — {count} template(s) loaded.")
        elif key == 1:
            try:
                description = input_popup(stdscr, "Add new template")
            except curses.error:
                description = None
            if description:
                run_opencode_interactive(str(SCRIPT_DIR), description)
            templates = load_templates(TEMPLATES_DIR)
            config = load_config()
            selected = {name: bool(config["templates"].get(name, False)) for name in templates}
            rebuild()
            persist()
            return "restart"

    output_lines = []
    for name in sorted(templates.keys()):
        if selected.get(name, False):
            body = templates[name]["body"].strip()
            if body:
                output_lines.append(body)
    output = "# AGENTS\n\n" + "\n\n".join(output_lines) + "\n"
    target_path = Path(target_dir) / "AGENTS.md"
    target_path.write_text(output)
    logger.info("Created %s", target_path)
    stdscr.keypad(False)
    return None


def run_main(target_dir: str) -> None:
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        logger.error(
            "make_agent_file.py requires an interactive terminal "
            "(a TTY is required for the selection UI)."
        )
        sys.exit(1)
    while True:
        stdscr = curses.initscr()
        try:
            result = main(stdscr, target_dir)
        except RuntimeError as exc:
            curses.endwin()
            logger.error("%s", exc)
            sys.exit(1)
        finally:
            try:
                curses.endwin()
            except curses.error:
                pass
        if result != "restart":
            return
        os.execv(sys.executable, [sys.executable, __file__, "select", target_dir])


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(levelname)s: %(message)s",
        )
    if ctx.invoked_subcommand is None:
        ctx.invoke(select)


@cli.command()
@click.argument("directory", default=os.getcwd())
@click.pass_context
def select(ctx, directory):
    run_main(directory)


@cli.command()
@click.argument("description", required=False, metavar="DESCRIPTION")
@click.pass_context
def add(ctx, description):
    if not description or not description.strip():
        click.echo(
            f"Error: '{ctx.command.name}' requires a non-empty DESCRIPTION "
            "(a natural language description of the template/s to create).",
            err=True,
        )
        click.echo(
            f"Usage: {ctx.command_path} DESCRIPTION",
            err=True,
        )
        click.echo(
            "Example: make_agent_file add \"a template for rust error handling\"",
            err=True,
        )
        ctx.exit(2)
    description = description.strip()
    run_opencode_interactive(str(SCRIPT_DIR), description)
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        logger.error(
            "make_agent_file.py requires an interactive terminal "
            "(a TTY is required for the selection UI)."
        )
        sys.exit(1)
    while True:
        stdscr = curses.initscr()
        try:
            result = main(stdscr, str(SCRIPT_DIR))
        except RuntimeError as exc:
            curses.endwin()
            logger.error("%s", exc)
            sys.exit(1)
        finally:
            try:
                curses.endwin()
            except curses.error:
                pass
        if result != "restart":
            return
        os.execv(sys.executable, [sys.executable, __file__, "select", str(SCRIPT_DIR)])


if __name__ == "__main__":
    cli()
