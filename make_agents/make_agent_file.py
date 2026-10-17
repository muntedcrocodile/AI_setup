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
import shlex
import subprocess
import textwrap
from typing import Any

import click

from configuration import load_metadata, load_program_config, save_ui_state
from input_popup import input_popup
from template_creator import run_opencode_interactive
from tree_builder import Node, Tree, load_templates

SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = SCRIPT_DIR / "agents_templates"
CONFIG_FILE = SCRIPT_DIR / "config.yml"
METADATA_FILE = SCRIPT_DIR / "metadata.yml"
LEGACY_CONFIG_FILE = SCRIPT_DIR / "template_config.json"

logger = logging.getLogger(__name__)


def build_tree(templates: dict[str, dict[str, Any]], metadata: dict[str, Any]) -> Tree:
    return Tree(
        templates,
        harness_models={
            name: settings["models"] for name, settings in metadata["harnesses"].items()
        },
    )


def draw_header(stdscr, target_dir: str) -> None:
    h, w = stdscr.getmaxyx()
    title = f" Select templates for {target_dir} "
    try:
        stdscr.addstr(0, 0, title.ljust(w)[:w], curses.A_REVERSE)
    except curses.error:
        pass


def draw_footer(stdscr) -> None:
    h, w = stdscr.getmaxyx()
    msg = " Space: toggle | ^E: edit | ←/→: collapse/expand | ^R: refresh | ^S: save | ^A: add | Enter: confirm | Esc: quit "
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


def edit_template(stdscr: "curses._CursesWindow", path: Path, editor: str) -> bool:
    """Open a template, suspending curses so terminal editors also work."""
    try:
        if not isinstance(editor, str) or not editor.strip():
            raise ValueError("editor must be a non-empty command string")
        command = shlex.split(editor)
        if not command or not command[0]:
            raise ValueError("editor must name an executable")
    except ValueError as exc:
        show_message(stdscr, f"Invalid editor setting: {exc}", 2500)
        return False

    error: str | None = None
    curses.def_prog_mode()
    curses.endwin()
    try:
        subprocess.run([*command, str(path.resolve())], check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        error = f"Could not open editor: {exc}"
    finally:
        curses.reset_prog_mode()
        stdscr.touchwin()
        stdscr.refresh()

    if error:
        show_message(stdscr, error, 2500)
        return False
    return True


def adjust_scroll(cursor_idx: int, scroll: int, visible_count: int, viewport_h: int) -> int:
    max_visible = viewport_h - 3
    if max_visible <= 0:
        return 0
    if cursor_idx < scroll:
        return cursor_idx
    if cursor_idx >= scroll + max_visible:
        return cursor_idx - max_visible + 1
    return max(0, scroll)


def draw_preview(
    stdscr: "curses._CursesWindow",
    node: Node | None,
    templates: dict[str, dict[str, Any]],
    scroll: int,
) -> int:
    """Draw the highlighted template's body and return its clamped scroll offset."""
    h, w = stdscr.getmaxyx()
    divider_x = w // 2
    x = divider_x + 2
    width = w - x - 1
    viewport_h = h - 4
    if width < 1 or viewport_h < 1:
        return 0

    if node is None:
        body = "No templates available."
    elif node.is_template:
        template = templates[node.template_name]
        meta = template["meta"]
        harnesses = ", ".join(meta["harness"]) or "general (unspecified)"
        models = ", ".join(meta["llm"]) or "All models (unspecified)"
        content = template["body"].strip() or "(Empty template)"
        body = f"Harnesses: {harnesses}\nModels: {models}\n\n{content}"
    else:
        body = f"{node.path}\n\nExpand this group with Right to preview its templates."

    lines: list[str] = []
    for line in body.expandtabs(4).splitlines():
        lines.extend(textwrap.wrap(line, width=width, replace_whitespace=False) or [""])
    scroll = max(0, min(scroll, max(0, len(lines) - viewport_h)))
    title = f"Preview: {node.name}" if node else "Preview"
    status = (
        f"PgUp/PgDn: scroll | {scroll + 1}-{min(scroll + viewport_h, len(lines))}/{len(lines)}"
        if len(lines) > viewport_h
        else "Full text"
    )
    try:
        stdscr.vline(1, divider_x, curses.ACS_VLINE, h - 2)
        stdscr.addnstr(1, x, title, width, curses.A_BOLD)
        for offset, line in enumerate(lines[scroll : scroll + viewport_h]):
            stdscr.addnstr(2 + offset, x, line, width)
        stdscr.addnstr(h - 2, x, status, width, curses.A_DIM)
    except curses.error:
        pass
    return scroll


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

    config = load_program_config(CONFIG_FILE, LEGACY_CONFIG_FILE)
    metadata = load_metadata(METADATA_FILE, LEGACY_CONFIG_FILE, templates)
    tree = build_tree(templates, metadata)
    available = set(tree.root.collect_template_names())
    selected = {
        name: bool(metadata["templates"].get(name, False)) and name in available
        for name in templates
    }
    tree.apply_expansion_state(metadata["ui_state"]["expanded_paths"])

    visible = tree.visible_nodes()
    cursor_idx = 0
    scroll = 0
    preview_scroll = 0
    preview_path: str | None = None

    def persist() -> None:
        nonlocal metadata
        metadata = save_ui_state(
            METADATA_FILE, LEGACY_CONFIG_FILE, templates, selected, tree.expanded_paths()
        )

    def refresh() -> int:
        """Re-read the template files from disk and rebuild the tree.

        Preserves the current cursor by path if that node still exists;
        otherwise falls back to the top of the list. Returns the number
        of templates now loaded so the caller can show a status message.
        """
        nonlocal templates, selected, tree, visible, cursor_idx, scroll, config, metadata
        prior_path = visible[cursor_idx].path if visible and 0 <= cursor_idx < len(visible) else ""
        # Load everything before changing the current UI, so invalid manual YAML
        # can be corrected while the existing picker remains usable.
        new_templates = load_templates(TEMPLATES_DIR)
        new_config = load_program_config(CONFIG_FILE, LEGACY_CONFIG_FILE)
        new_metadata = load_metadata(METADATA_FILE, LEGACY_CONFIG_FILE, new_templates)
        templates, config, metadata = new_templates, new_config, new_metadata
        tree = build_tree(templates, metadata)
        available = set(tree.root.collect_template_names())
        selected = {
            name: bool(metadata["templates"].get(name, False)) and name in available
            for name in templates
        }
        tree.apply_expansion_state(metadata["ui_state"]["expanded_paths"])
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
        list_width = w // 2
        draw_header(stdscr, target_dir)
        scroll = adjust_scroll(cursor_idx, scroll, len(visible), h)
        current_node = visible[cursor_idx] if visible else None
        current_path = current_node.path if current_node else None
        if current_path != preview_path:
            preview_scroll = 0
            preview_path = current_path

        body_start_y = 1
        if scroll > 0:
            try:
                stdscr.addstr(
                    body_start_y,
                    0,
                    f"  … {scroll} hidden above".ljust(list_width)[:list_width],
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
                width=list_width,
                selected=selected,
                is_cursor=(scroll + offset == cursor_idx),
            )
        preview_scroll = draw_preview(stdscr, current_node, templates, preview_scroll)
        draw_footer(stdscr)
        stdscr.refresh()

        key = stdscr.getch()

        if key == 27:
            persist()
            return None
        if not visible and key not in (18, 1):
            continue
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
        elif key == curses.KEY_PPAGE:
            preview_scroll -= max(1, h - 4)
        elif key == curses.KEY_NPAGE:
            preview_scroll += max(1, h - 4)
        elif key == 5:
            node = visible[cursor_idx]
            if not node.is_template:
                show_message(stdscr, "Highlight a template file to edit.")
            elif edit_template(stdscr, templates[node.template_name]["path"], config["editor"]):
                try:
                    refresh()
                except RuntimeError as exc:
                    show_message(stdscr, str(exc), 2500)
                    continue
                preview_scroll = 0
                show_message(stdscr, "Editor opened. Ctrl+R reloads saved changes.")
        elif key == 19:
            persist()
            show_message(stdscr, "Defaults saved!")
        elif key == 18:
            try:
                count = refresh()
            except RuntimeError as exc:
                show_message(stdscr, str(exc), 2500)
                continue
            persist()
            show_message(stdscr, f"Refreshed — {count} template(s) loaded.")
        elif key == 1:
            try:
                description = input_popup(stdscr, "Add new template")
            except curses.error:
                description = None
            if description:
                run_opencode_interactive(str(SCRIPT_DIR), description)
            refresh()
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
@click.option(
    "--directory",
    default=None,
    help="Target directory where AGENTS.md will be written. Defaults to the current working directory.",
)
@click.pass_context
def add(ctx, description, directory: str | None):
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
    original_cwd = os.getcwd()
    target_dir = directory if directory is not None else original_cwd
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


if __name__ == "__main__":
    cli()
