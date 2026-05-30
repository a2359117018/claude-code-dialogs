# Claude Code Windows Hooks — AI Setup Guide

> **Usage**: Copy this entire file and paste it to your AI assistant (Claude Code, ChatGPT, etc.), then say "帮我安装". The AI will handle everything below automatically.

---

## What This Installs

Four native Windows GUI hooks for Claude Code CLI — zero external dependencies, powered by Python + tkinter:

| Hook | Event | Function |
|------|-------|----------|
| Permission Request | `PermissionRequest` | Allow/Deny dialog with session/project/global suggestion buttons |
| Ask User Question | `PreToolUse` → `AskUserQuestion` | Native option dialog (single/multi select) |
| Stop Notify | `Stop` | OSC 9 terminal notification when Claude finishes |
| Exit Plan Mode | `PermissionRequest` → `ExitPlanMode` | Topmost messagebox when plan is ready (auto-closes 25s) |

**Requirements**: Windows 10/11, Python 3.10+ with tkinter, Claude Code CLI.

---

## AI Instructions

Follow these steps in order. Do NOT skip verification.

### Step 1: Create hook scripts directory

```
<USER_HOME>/.claude/hooks/scripts/
```

Create this directory if it doesn't exist. This is the standard location for Claude Code hook scripts.

### Step 2: Create hook scripts

Create the following 4 files in `<USER_HOME>/.claude/hooks/scripts/`. Use the EXACT content below — do not modify.

#### File 1: `permission_request.pyw`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Code PermissionRequest hook.

Reads JSON from stdin (UTF-8), shows Allow/Deny dialog,
outputs JSON decision to stdout.
"""

import json
import sys
import tkinter as tk
from tkinter import scrolledtext

# Fix encoding on Windows
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

MAX_WIDTH = 600
MAX_HEIGHT = 520
MIN_HEIGHT = 160

SUGGESTION_LABELS = {
    ("addRules", "allow", "session"):       "Allow for Session",
    ("addRules", "allow", "localSettings"): "Always Allow (Project)",
    ("addRules", "allow", "userSettings"):  "Always Allow (Global)",
    ("addRules", "deny", "session"):        "Deny for Session",
    ("addRules", "deny", "localSettings"):  "Always Deny (Project)",
    ("addRules", "deny", "userSettings"):   "Always Deny (Global)",
    ("setMode", "auto", "session"):         "Auto Approve (Session)",
    ("setMode", "auto", "localSettings"):   "Auto Approve (Project)",
    ("setMode", "plan", "session"):         "Plan Mode (Session)",
}


def get_suggestion_label(suggestion: dict) -> str:
    sug_type = suggestion.get("type", "")
    behavior = suggestion.get("decision", {}).get("behavior", "")
    dest = suggestion.get("decision", {}).get("destination", "")
    return SUGGESTION_LABELS.get((sug_type, behavior, dest), "Apply Rule")


def shorten_path(path: str) -> str:
    path = path.replace("/", "\\")
    parts = path.rstrip("\\").rsplit("\\", 1)
    if len(parts) == 2:
        return f"...\\{parts[1]}" if len(parts[0]) > 30 else path
    return path


def build_permission_message(data: dict) -> tuple[str, str]:
    tool_name = data.get("tool_name", "Unknown")
    tool_input = data.get("tool_input", {})

    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        title = "Bash Command"
        body = cmd if cmd else "(empty command)"
        if len(body) > 300:
            body = body[:300] + "\n... (truncated)"
    elif tool_name == "Edit":
        title = "Edit File"
        body = shorten_path(tool_input.get("file_path", "Unknown"))
    elif tool_name == "Write":
        title = "Write File"
        body = shorten_path(tool_input.get("file_path", "Unknown"))
    elif tool_name == "Read":
        title = "Read File"
        body = shorten_path(tool_input.get("file_path", "Unknown"))
    else:
        title = f"Permission \u2014 {tool_name}"
        display = {}
        for k, v in list(tool_input.items())[:5]:
            s = str(v)
            display[k] = s[:80] + "..." if len(s) > 80 else s
        body = json.dumps(display, ensure_ascii=False, indent=2)
        if len(body) > 200:
            body = body[:200] + "\n... (truncated)"

    return title, body


def _center_dialog(dialog: tk.Toplevel, width: int = None, height: int = None):
    dialog.update_idletasks()
    screen_w = dialog.winfo_screenwidth()
    screen_h = dialog.winfo_screenheight()
    w = min(max(width or dialog.winfo_reqwidth(), 440), MAX_WIDTH)
    h = min(max(height or dialog.winfo_reqheight(), MIN_HEIGHT), MAX_HEIGHT)
    x = (screen_w - w) // 2
    y = (screen_h - h) // 2
    dialog.geometry(f"{w}x{h}+{x}+{y}")
    dialog.minsize(400, MIN_HEIGHT)


def show_permission_dialog(title: str, body: str, suggestions: list[dict]) -> tuple[str, dict | None]:
    root = tk.Tk()
    root.withdraw()

    dialog = tk.Toplevel(root)
    dialog.title("Claude Code")
    dialog.resizable(True, False)
    dialog.attributes("-topmost", True)

    # Title
    tk.Label(dialog, text=title, font=("Microsoft YaHei UI", 12, "bold"),
             anchor="w").pack(fill="x", padx=20, pady=(15, 8))

    tk.Frame(dialog, height=1, relief="sunken", bd=1).pack(fill="x", padx=20)

    # Scrollable content
    content_frame = tk.Frame(dialog)
    content_frame.pack(fill="both", expand=True, padx=10, pady=8)

    text_widget = scrolledtext.ScrolledText(
        content_frame, wrap="word", height=6,
        padx=10, pady=8, state="normal",
    )
    text_widget.pack(fill="both", expand=True)
    text_widget.insert("1.0", body)
    text_widget.configure(state="disabled")

    tk.Frame(dialog, height=1, relief="sunken", bd=1).pack(fill="x", padx=20)

    # --- Bottom: Allow/Deny (pack FIRST with side=bottom) ---
    action_frame = tk.Frame(dialog)
    action_frame.pack(fill="x", padx=20, pady=(10, 15), side="bottom")

    tk.Frame(action_frame).pack(side="left", expand=True)

    result = {"behavior": None, "suggestion": None}

    def make_decision(behavior: str, suggestion: dict | None):
        result["behavior"] = behavior
        result["suggestion"] = suggestion
        dialog.destroy()

    def on_deny():
        make_decision("deny", None)

    tk.Button(action_frame, text="\u2715  Deny", command=on_deny,
              padx=18, pady=6).pack(side="right", padx=(8, 0))

    def on_allow():
        make_decision("allow", None)

    allow_btn = tk.Button(action_frame, text="\u2713  Allow", command=on_allow,
                          padx=18, pady=6)
    allow_btn.pack(side="right")

    allow_btn.focus_set()
    dialog.bind("<Return>", lambda e: on_allow())
    dialog.bind("<Escape>", lambda e: on_deny())
    dialog.protocol("WM_DELETE_WINDOW", on_deny)

    # --- Suggestion buttons (pack SECOND with side=bottom, above Allow/Deny) ---
    if suggestions:
        sug_frame = tk.Frame(dialog)
        sug_frame.pack(fill="x", padx=20, side="bottom")

        tk.Frame(sug_frame, height=1, relief="sunken", bd=1).pack(fill="x", pady=(0, 8))

        sug_inner = tk.Frame(sug_frame)
        sug_inner.pack(anchor="w")

        col = 0
        max_cols = 2
        for i, sug in enumerate(suggestions):
            label = get_suggestion_label(sug)
            sug_behavior = sug.get("decision", {}).get("behavior", "allow")
            idx = i + 1

            def on_suggestion(s=sug, b=sug_behavior):
                make_decision(b, s)

            tk.Button(
                sug_inner, text=f"{idx}. {label}", command=on_suggestion,
                width=22, anchor="w", padx=12, pady=5,
            ).grid(row=col // max_cols, column=col % max_cols, padx=(0, 8), pady=(0, 4), sticky="w")
            col += 1

            if idx <= 9:
                dialog.bind(str(idx), lambda e, fn=on_suggestion: fn())

    _center_dialog(dialog)
    dialog.wait_window()
    root.destroy()

    return result.get("behavior", "deny"), result.get("suggestion")


def main():
    try:
        raw = sys.stdin.buffer.read()
        data = json.loads(raw.decode("utf-8"))
    except Exception:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PermissionRequest",
                "decision": {"behavior": "deny", "message": "Failed to parse hook input"},
            }
        }))
        sys.exit(0)

    title, body = build_permission_message(data)
    suggestions = data.get("permission_suggestions", [])
    behavior, selected_suggestion = show_permission_dialog(title, body, suggestions)

    if behavior == "allow" and selected_suggestion:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PermissionRequest",
                "decision": {
                    "behavior": "allow",
                    "updatedPermissions": [selected_suggestion],
                }
            }
        }
    elif behavior == "deny" and selected_suggestion:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PermissionRequest",
                "decision": {
                    "behavior": "deny",
                    "message": "Denied by user via GUI dialog",
                    "updatedPermissions": [selected_suggestion],
                }
            }
        }
    elif behavior == "allow":
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PermissionRequest",
                "decision": {"behavior": "allow"},
            }
        }
    else:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PermissionRequest",
                "decision": {"behavior": "deny", "message": "Denied by user via GUI dialog"},
            }
        }

    print(json.dumps(output, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
```

#### File 2: `ask_user_question.pyw`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Code PreToolUse hook for AskUserQuestion.

Triggered via settings.json:
  PreToolUse -> matcher: "AskUserQuestion"

Reads JSON from stdin (UTF-8), shows question dialog with native
Checkbutton (single select with mutual exclusion) or Checkbutton (multi select),
outputs JSON decision to stdout.

Output format (per docs):
  hookSpecificOutput:
    hookEventName: "PreToolUse"
    permissionDecision: "allow"
    updatedInput:
      questions: [...]       # echo back original
      answers: {"question text": "selected label"}  # or ["label1", "label2"] for multi
"""

import json
import sys
import tkinter as tk

# Fix encoding on Windows
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

MAX_WIDTH = 580
MAX_HEIGHT = 520
MIN_HEIGHT = 200


def _center_dialog(dialog: tk.Toplevel, width: int = None, height: int = None):
    dialog.update_idletasks()
    screen_w = dialog.winfo_screenwidth()
    screen_h = dialog.winfo_screenheight()
    w = min(max(width or dialog.winfo_reqwidth(), 440), MAX_WIDTH)
    h = min(max(height or dialog.winfo_reqheight(), MIN_HEIGHT), MAX_HEIGHT)
    x = (screen_w - w) // 2
    y = (screen_h - h) // 2
    dialog.geometry(f"{w}x{h}+{x}+{y}")
    dialog.minsize(400, MIN_HEIGHT)


def show_question_dialog(questions: list[dict]) -> dict | None:
    """
    Show dialog for AskUserQuestion format.
    Returns answers dict {question_text: label_or_list} or None if cancelled.
    """
    root = tk.Tk()
    root.withdraw()

    dialog = tk.Toplevel(root)
    dialog.title("Claude Code \u2014 Question")
    dialog.resizable(True, True)
    dialog.attributes("-topmost", True)

    result_cancelled = {"value": False}

    # --- Bottom buttons (pack FIRST so they stay visible) ---
    btn_area = tk.Frame(dialog)
    btn_area.pack(fill="x", padx=20, pady=(10, 15), side="bottom")

    tk.Frame(btn_area, height=1, relief="sunken", bd=1).pack(fill="x", pady=(0, 10))

    action_frame = tk.Frame(btn_area)
    action_frame.pack(fill="x")

    tk.Frame(action_frame).pack(side="left", expand=True)

    def on_cancel():
        result_cancelled["value"] = True
        dialog.destroy()

    tk.Button(action_frame, text="\u2715  Cancel", command=on_cancel,
              padx=18, pady=6).pack(side="right", padx=(8, 0))

    def on_confirm():
        dialog.destroy()

    confirm_btn = tk.Button(action_frame, text="\u2713  Confirm", command=on_confirm,
                            padx=18, pady=6)
    confirm_btn.pack(side="right")

    confirm_btn.focus_set()
    dialog.bind("<Return>", lambda e: on_confirm())
    dialog.bind("<Escape>", lambda e: on_cancel())
    dialog.protocol("WM_DELETE_WINDOW", on_cancel)

    # --- Title ---
    tk.Label(dialog, text="Claude is asking a question",
             anchor="w").pack(fill="x", padx=20, pady=(15, 8))

    tk.Frame(dialog, height=1, relief="sunken", bd=1).pack(fill="x", padx=20)

    # --- Scrollable content ---
    scroll_container = tk.Frame(dialog)
    scroll_container.pack(fill="both", expand=True)

    canvas = tk.Canvas(scroll_container, highlightthickness=0)
    scrollbar = tk.Scrollbar(scroll_container, orient="vertical", command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)

    scroll_frame = tk.Frame(canvas)
    scroll_window = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

    def on_frame_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def on_canvas_configure(event):
        canvas.itemconfig(scroll_window, width=event.width)

    scroll_frame.bind("<Configure>", on_frame_configure)
    canvas.bind("<Configure>", on_canvas_configure)

    def on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    canvas.bind_all("<MouseWheel>", on_mousewheel)

    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)

    # --- Build questions ---
    question_vars: list[dict] = []

    for q_idx, q in enumerate(questions):
        q_frame = tk.Frame(scroll_frame)
        q_frame.pack(fill="x", padx=20, pady=(12, 4))

        # Header chip
        header = q.get("header", "")
        if header:
            tk.Label(q_frame, text=header, relief="groove", bd=1,
                     padx=6, pady=2).pack(anchor="w", pady=(0, 6))

        # Question text
        question_text = q.get("question", "")
        tk.Label(q_frame, text=question_text, wraplength=520,
                 justify="left", anchor="w").pack(fill="x", anchor="w", pady=(0, 8))

        options = q.get("options", [])
        multi = q.get("multiSelect", False)

        if multi:
            cb_vars: list[tk.BooleanVar] = []

            for i, opt in enumerate(options):
                var = tk.BooleanVar(value=False)
                cb_vars.append(var)

                opt_frame = tk.Frame(q_frame)
                opt_frame.pack(fill="x", pady=(0, 2))

                cb = tk.Checkbutton(
                    opt_frame, text=opt.get("label", ""), variable=var,
                    anchor="w", wraplength=520,
                )
                cb.pack(anchor="w", padx=4)

                def make_frame_toggle(v):
                    def onClick(event):
                        v.set(not v.get())
                    return onClick
                opt_frame.bind("<Button-1>", make_frame_toggle(var))

                desc = opt.get("description", "")
                if desc:
                    tk.Label(opt_frame, text=desc, wraplength=500,
                             justify="left", anchor="w").pack(anchor="w", padx=28, pady=(0, 4))

            question_vars.append({
                "question": question_text,
                "multi": True,
                "vars": cb_vars,
                "options": options,
            })
        else:
            # Single select: Checkbutton + trace for mutual exclusion
            cb_vars: list[tk.BooleanVar] = []

            for i, opt in enumerate(options):
                var = tk.BooleanVar(value=False)
                cb_vars.append(var)

                opt_frame = tk.Frame(q_frame)
                opt_frame.pack(fill="x", pady=(0, 2))

                def make_trace(idx, v, all_vars):
                    def on_change(*args):
                        if v.get():
                            for j, v2 in enumerate(all_vars):
                                if j != idx:
                                    v2.set(False)
                    return on_change

                var.trace_add("write", make_trace(i, var, cb_vars))

                cb = tk.Checkbutton(
                    opt_frame, text=opt.get("label", ""), variable=var,
                    anchor="w", wraplength=520,
                )
                cb.pack(anchor="w", padx=4)

                def make_frame_toggle(v):
                    def onClick(event):
                        v.set(not v.get())
                    return onClick
                opt_frame.bind("<Button-1>", make_frame_toggle(var))

                desc = opt.get("description", "")
                if desc:
                    tk.Label(opt_frame, text=desc, wraplength=500,
                             justify="left", anchor="w").pack(anchor="w", padx=28, pady=(0, 4))

            question_vars.append({
                "question": question_text,
                "multi": False,
                "vars": cb_vars,
                "options": options,
            })

        # Separator between questions
        if q_idx < len(questions) - 1:
            tk.Frame(scroll_frame, height=1, relief="sunken", bd=1).pack(fill="x", padx=20, pady=(8, 0))

    _center_dialog(dialog, width=MAX_WIDTH, height=MAX_HEIGHT)
    dialog.wait_window()
    root.destroy()

    if result_cancelled["value"]:
        return None

    # Build answers dict: {question_text: selected_label_or_list}
    answers = {}
    for qv in question_vars:
        selected = [qv["options"][i].get("label", "") for i, v in enumerate(qv["vars"]) if v.get()]
        if qv["multi"]:
            answers[qv["question"]] = selected if selected else ""
        else:
            answers[qv["question"]] = selected[0] if selected else qv["options"][0].get("label", "")

    return answers


def main():
    try:
        raw = sys.stdin.buffer.read()
        data = json.loads(raw.decode("utf-8"))
    except Exception:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "Failed to parse hook input",
            }
        }))
        sys.exit(0)

    tool_input = data.get("tool_input", {})
    questions = tool_input.get("questions", [])

    if not questions:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "No questions found in input",
            }
        }))
        sys.exit(0)

    answers = show_question_dialog(questions)

    if answers is None:
        # User cancelled
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "User cancelled the question dialog",
            }
        }))
    else:
        # Per docs: echo back original questions + add answers
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "updatedInput": {
                    "questions": questions,
                    "answers": answers,
                }
            }
        }, ensure_ascii=False))

    sys.exit(0)


if __name__ == "__main__":
    main()
```

#### File 3: `stop_notify.pyw`

```python
#!/usr/bin/env python3
"""
Claude Code Stop hook.

When Claude finishes responding and waits for user input,
emits an OSC 9 terminal notification sequence via stdout.
Claude Code then sends it through its own terminal write path,
triggering a desktop notification in Windows Terminal / iTerm2 / WezTerm etc.

Reads JSON from stdin. Outputs JSON with terminalSequence to stdout.
"""

import json
import sys


def main():
    # Read and discard stdin JSON (Claude Code sends event context)
    try:
        sys.stdin.read()
    except Exception:
        pass

    # OSC 9 notification sequence: \033]9;title;body\007
    # Supported by Windows Terminal, iTerm2, WezTerm, ConEmu, etc.
    seq = "\033]9;Claude Code;Task completed\007"

    result = {"terminalSequence": seq}
    print(json.dumps(result, ensure_ascii=False))

    sys.exit(0)


if __name__ == "__main__":
    main()
```

#### File 4: `exit_plan_mode_notify.pyw`

```python
#!/usr/bin/env python3
"""
Claude Code PermissionRequest hook — ExitPlanMode event.

Shows a topmost tkinter message box when ExitPlanMode fires.
No third-party dependencies required.

Auto-closes after ~25 seconds (configurable via AUTO_CLOSE_MS).
"""

import sys
import tkinter as tk
from tkinter import messagebox

AUTO_CLOSE_MS = 25000  # 25 seconds


def show_notification():
    root = tk.Tk()
    root.withdraw()  # hide root window
    root.attributes("-topmost", True)

    # Schedule auto-close
    root.after(AUTO_CLOSE_MS, root.destroy)

    messagebox.showinfo(
        "Claude Code",
        "Plan is ready. Please review and approve.",
        parent=root,
    )
    root.destroy()


def main():
    # Read and discard stdin JSON
    try:
        sys.stdin.read()
    except Exception:
        pass

    show_notification()

    # No decision output needed
    sys.exit(0)


if __name__ == "__main__":
    main()
```

### Step 3: Configure settings.json

Read the existing `~/.claude/settings.json`. If it already has a `"hooks"` key, **merge** the configuration below into it (do NOT overwrite existing hooks). If it has no `"hooks"` key, add the entire `"hooks"` block.

The final `"hooks"` section must contain:

```json
{
  "hooks": {
    "PermissionRequest": [
      {
        "matcher": "Bash|Edit|Write|Read|Glob|Grep|WebFetch|WebSearch|mcp__.*",
        "hooks": [
          {
            "type": "command",
            "command": "pythonw ~/.claude/hooks/scripts/permission_request.pyw"
          }
        ]
      },
      {
        "matcher": "ExitPlanMode",
        "hooks": [
          {
            "type": "command",
            "command": "pythonw ~/.claude/hooks/scripts/exit_plan_mode_notify.pyw"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "AskUserQuestion",
        "hooks": [
          {
            "type": "command",
            "command": "pythonw ~/.claude/hooks/scripts/ask_user_question.pyw"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "pythonw ~/.claude/hooks/scripts/stop_notify.pyw"
          }
        ]
      }
    ]
  }
}
```

**Important**:
- On Windows, `~` resolves to `C:\Users\<USERNAME>`. Use `~` as-is — Claude Code expands it automatically.
- Use `pythonw` (not `python`) to prevent console window flash.
- The `mcp__.*` regex is required to match MCP tool permissions (e.g. `mcp__filesystem__list_directory`).

### Step 4: Verify

Run each verification check. All must pass before reporting success.

1. **File existence** — Confirm all 4 `.pyw` files exist in `~/.claude/hooks/scripts/`
2. **Python availability** — Run `pythonw --version` and confirm Python 3.10+
3. **tkinter available** — Run `pythonw -c "import tkinter; print('ok')"` and confirm it prints `ok`
4. **settings.json valid** — Parse `~/.claude/settings.json` as JSON and confirm no syntax errors
5. **Hook config present** — Confirm `hooks.PermissionRequest`, `hooks.PreToolUse`, and `hooks.Stop` all exist in settings.json

### Step 5: Report

Tell the user:
- Which files were created
- Whether settings.json was created new or merged into existing
- Any warnings (e.g. tkinter not available, old hooks overwritten)
- That they need to **restart their Claude Code session** for hooks to take effect

---

## Troubleshooting

- **Console window flashes**: Make sure `command` uses `pythonw` not `python`
- **No dialog appears**: Check that `pythonw -c "import tkinter"` works; some minimal Python installs exclude tkinter
- **Hooks not triggering**: Restart the Claude Code session; hooks are loaded at session start
- **OSC 9 notification not showing**: Requires a modern terminal (Windows Terminal, WezTerm, etc.); legacy cmd.exe does not support OSC 9
