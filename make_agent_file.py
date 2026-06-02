#!/usr/bin/env python3
import argparse
import json
import os
import sys
from pathlib import Path

try:
    import curses
except ImportError:
    print("curses module not available on this platform")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent
TEMPLATES_DIR = SCRIPT_DIR / "agents_templates"
CONFIG_FILE = SCRIPT_DIR / "template_config.json"

DEFAULT_CONFIG = {
    "templates": {}
}

def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return DEFAULT_CONFIG

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

def get_templates():
    templates = {}
    if TEMPLATES_DIR.exists():
        for f in TEMPLATES_DIR.glob("*.md"):
            templates[f.stem] = f.read_text()
    return templates

def main(stdscr, target_dir):
    templates = get_templates()
    if not templates:
        stdscr.addstr(0, 0, "No templates found in agents_templates/")
        stdscr.getch()
        return

    config = load_config()
    defaults = config.get("templates", {})

    selected = {name: defaults.get(name, True) for name in templates}

    curses.curs_set(0)
    stdscr.clear()
    height, width = stdscr.getmaxyx()

    current_idx = 0
    template_names = sorted(templates.keys())

    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()

        title = f"Select templates for {target_dir}"
        stdscr.addstr(0, 0, title, curses.A_REVERSE)

        for i, name in enumerate(template_names):
            y = i + 2
            if y >= h - 1:
                break
            prefix = "[x]" if selected[name] else "[ ]"
            attr = curses.A_REVERSE if i == current_idx else curses.A_NORMAL
            stdscr.addstr(y, 0, f" {prefix} {name}", attr)

        stdscr.addstr(h - 2, 0, "Space: toggle | Enter: confirm | Esc: quit", curses.A_DIM)

        key = stdscr.getch()

        if key == 27:
            return
        elif key == ord("\n"):
            break
        elif key == ord(" "):
            selected[template_names[current_idx]] = not selected[template_names[current_idx]]
        elif key == curses.KEY_UP and current_idx > 0:
            current_idx -= 1
        elif key == curses.KEY_DOWN and current_idx < len(template_names) - 1:
            current_idx += 1

    config["templates"] = selected
    save_config(config)

    output_lines = []
    for name in sorted(template_names):
        if selected[name]:
            output_lines.append(templates[name].strip())

    output = "# AGENTS\n\n" + "\n\n".join(output_lines)
    target_path = Path(target_dir) / "AGENTS.md"
    target_path.write_text(output + "\n")

    print(f"Created {target_path}")
    return

def handle_interrupt(signum, frame):
    print("\nInterrupted by user")
    sys.exit(0)

if __name__ == "__main__":
    import signal
    signal.signal(signal.SIGINT, handle_interrupt)
    
    parser = argparse.ArgumentParser(description="Create AGENTS.md from templates")
    parser.add_argument("directory", nargs="?", default=os.getcwd(), help="Target directory")
    args = parser.parse_args()

    curses.wrapper(lambda stdscr: main(stdscr, args.directory))