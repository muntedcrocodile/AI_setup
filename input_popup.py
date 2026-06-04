import re
import logging
import curses
from pathlib import Path
from blessed import Terminal

LOG_FILE = Path(__file__).parent / "input_popup.log"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="w"),
    ]
)
logger = logging.getLogger(__name__)


def input_popup(stdscr, prompt_text):
    curses.endwin()
    
    logger.info("=== input_popup started ===")
    
    term = Terminal()
    cursor_y = 0
    cursor_x = 0
    scroll_y = 0
    lines = [""]
    
    h = term.height
    w = term.width
    
    with term.fullscreen(), term.cbreak(), term.enable_kitty_keyboard(report_events=True):
        
        def get_visible_lines():
            visible = []
            start_y = 1
            max_visible = h - 2
            for i in range(max_visible):
                idx = scroll_y + i
                if idx < len(lines):
                    visible.append((start_y + i, idx, lines[idx]))
            return visible
        
        def redraw():
            print(term.clear + term.move(0, 0) + prompt_text)
            print(term.move(h - 1, 0) + term.on_black + term.white + " Enter: save | Shift+Enter: new line | Esc: cancel " + term.normal)
            
            for y, idx, line in get_visible_lines():
                display_line = line[:w - 1] if len(line) > w - 1 else line
                print(term.move(y, 0) + display_line)
            
            display_y = 1 + (cursor_y - scroll_y)
            display_x = min(cursor_x, w - 1)
            print(term.move(display_y, display_x), end="", flush=True)
        
        def jump_word_right():
            nonlocal cursor_x
            line = lines[cursor_y]
            remaining = line[cursor_x:]
            match = re.search(r'\S', remaining)
            if match:
                cursor_x += match.start()
                remaining2 = line[cursor_x:]
                match2 = re.search(r'\s', remaining2)
                if match2:
                    cursor_x += match2.start()
                else:
                    cursor_x = len(line)
            else:
                cursor_x = len(line)
        
        def jump_word_left():
            nonlocal cursor_x
            line = lines[cursor_y]
            before = line[:cursor_x]
            if not before:
                cursor_x = 0
                return
            match = list(re.finditer(r'\S', before))
            if match:
                last_word = match[-1]
                word_start = last_word.start()
                before_word = before[:word_start]
                match_ws = list(re.finditer(r'\s', before_word))
                if match_ws:
                    cursor_x = match_ws[-1].start() + 1
                else:
                    cursor_x = word_start
            else:
                cursor_x = 0
        
        def delete_word_left():
            nonlocal cursor_x
            if cursor_x == 0:
                return
            line = lines[cursor_y]
            before = line[:cursor_x]
            match = list(re.finditer(r'\S', before))
            if match:
                last_word = match[-1]
                word_start = last_word.start()
                before_word = before[:word_start]
                match_ws = list(re.finditer(r'\s', before_word))
                delete_from = match_ws[-1].start() + 1 if match_ws else 0
            else:
                delete_from = 0
            lines[cursor_y] = line[:delete_from] + line[cursor_x:]
            cursor_x = delete_from
        
        def delete_word_right():
            nonlocal cursor_x
            line = lines[cursor_y]
            remaining = line[cursor_x:]
            match = re.search(r'\S', remaining)
            if match:
                cursor_x += match.start()
                match2 = re.search(r'\s', line[cursor_x:])
                if match2:
                    end_pos = cursor_x + match2.start()
                    lines[cursor_y] = line[:cursor_x] + line[end_pos:]
                else:
                    lines[cursor_y] = line[:cursor_x]
        
        def do_newline():
            nonlocal cursor_y, cursor_x
            line = lines[cursor_y]
            before = line[:cursor_x]
            after = line[cursor_x:]
            lines[cursor_y] = before
            lines.insert(cursor_y + 1, after)
            cursor_y += 1
            cursor_x = 0
        
        def do_backspace():
            nonlocal cursor_y, cursor_x
            if cursor_x > 0:
                lines[cursor_y] = lines[cursor_y][:cursor_x - 1] + lines[cursor_y][cursor_x:]
                cursor_x -= 1
            elif cursor_y > 0:
                cursor_x = len(lines[cursor_y - 1])
                lines[cursor_y - 1] += lines[cursor_y]
                lines.pop(cursor_y)
                cursor_y -= 1
        
        def do_delete():
            nonlocal cursor_y
            if cursor_x < len(lines[cursor_y]):
                lines[cursor_y] = lines[cursor_y][:cursor_x] + lines[cursor_y][cursor_x + 1:]
            elif cursor_y < len(lines) - 1:
                lines[cursor_y] += lines[cursor_y + 1]
                lines.pop(cursor_y + 1)
        
        def do_up():
            nonlocal cursor_y, cursor_x
            if cursor_y > 0:
                cursor_y -= 1
                cursor_x = min(cursor_x, len(lines[cursor_y]))
        
        def do_down():
            nonlocal cursor_y, cursor_x
            if cursor_y < len(lines) - 1:
                cursor_y += 1
                cursor_x = min(cursor_x, len(lines[cursor_y]))
        
        def do_left():
            nonlocal cursor_y, cursor_x
            if cursor_x > 0:
                cursor_x -= 1
            elif cursor_y > 0:
                cursor_y -= 1
                cursor_x = len(lines[cursor_y])
        
        def do_right():
            nonlocal cursor_y, cursor_x
            if cursor_x < len(lines[cursor_y]):
                cursor_x += 1
            elif cursor_y < len(lines) - 1:
                cursor_y += 1
                cursor_x = 0
        
        def do_home():
            nonlocal cursor_x
            cursor_x = 0
        
        def do_end():
            nonlocal cursor_x
            cursor_x = len(lines[cursor_y])
        
        def do_char(ch):
            nonlocal cursor_x
            lines[cursor_y] = lines[cursor_y][:cursor_x] + ch + lines[cursor_y][cursor_x:]
            cursor_x += 1
        
        def do_nop():
            pass
        
        handlers = {
            "KEY_ESCAPE": lambda: "ESCAPE",
            "KEY_ENTER": lambda: "SAVE",
            "KEY_SHIFT_ENTER": do_newline,
            "KEY_BACKSPACE": do_backspace,
            "KEY_DELETE": do_delete,
            "KEY_UP": do_up,
            "KEY_DOWN": do_down,
            "KEY_LEFT": do_left,
            "KEY_RIGHT": do_right,
            "KEY_HOME": do_home,
            "KEY_END": do_end,
            "KEY_CTRL_LEFT": jump_word_left,
            "KEY_CTRL_RIGHT": jump_word_right,
            "KEY_CTRL_BACKSPACE": delete_word_left,
            "KEY_CTRL_DELETE": delete_word_right,
        }
        
        redraw()
        
        while True:
            try:
                key = term.inkey(timeout=60)
            except KeyboardInterrupt:
                continue
            
            if not key:
                continue
            
            logger.info("key=%r, name=%s", key, key.name)
            
            if key.name and key.name.endswith("_RELEASED"):
                continue
            
            if key.name == "KEY_ESCAPE":
                return None
            
            if key.name == "KEY_ENTER":
                return "\n".join(lines).strip()
            
            handler = handlers.get(key.name, do_nop)
            handler()
            
            if not key.is_sequence and not key.name and len(key) == 1:
                logger.info("  char '%s'", key)
                do_char(str(key))
            
            if cursor_y < scroll_y:
                scroll_y = cursor_y
            elif cursor_y >= scroll_y + h - 3:
                scroll_y = cursor_y - h + 4
            
            redraw()