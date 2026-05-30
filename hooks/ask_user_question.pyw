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
    # For each question, store a tk.StringVar (single) or list of tk.BooleanVar (multi)
    question_vars: list[dict] = []  # {"question": str, "multi": bool, "var": StringVar|list[BooleanVar], "options": list[dict]}

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
            # Multi select: Checkbutton variable handles toggle automatically.
            # No command or extra bindings needed - tkinter toggles the variable on click.
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

                # Click on frame area toggles the variable (allows clicking label area)
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

                # Trace: when var changes to True, deselect others
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

                # Click on frame area toggles the variable
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
