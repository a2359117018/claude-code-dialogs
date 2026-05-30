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
