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
