# Claude Code Windows Hooks — Install Skill

You are helping the user install Claude Code Windows GUI hooks.

## What This Installs

Four native Windows GUI hooks for Claude Code CLI — zero external dependencies, powered by Python + tkinter.

| Hook | Event | Function |
|------|-------|----------|
| `permission_request.pyw` | `PermissionRequest` | Allow/Deny dialog with suggestion buttons |
| `ask_user_question.pyw` | `PreToolUse` → `AskUserQuestion` | Native option dialog (single/multi select) |
| `stop_notify.pyw` | `Stop` | OSC 9 terminal notification |
| `exit_plan_mode_notify.pyw` | `PermissionRequest` → `ExitPlanMode` | Topmost messagebox (auto-closes 25s) |

## Installation Steps

### Step 1: Create target directory

Create `~/.claude/hooks/scripts/` if it does not exist.

### Step 2: Download hook scripts

Download these 4 files (via `curl`, `wget`, or Python `urllib`) to `~/.claude/hooks/scripts/`:

```
https://raw.githubusercontent.com/a2359117018/claude-code-dialogs/main/hooks/permission_request.pyw
https://raw.githubusercontent.com/a2359117018/claude-code-dialogs/main/hooks/ask_user_question.pyw
https://raw.githubusercontent.com/a2359117018/claude-code-dialogs/main/hooks/stop_notify.pyw
https://raw.githubusercontent.com/a2359117018/claude-code-dialogs/main/hooks/exit_plan_mode_notify.pyw
```

After downloading, verify all 4 files exist and are non-empty.

### Step 3: Configure `~/.claude/settings.json`

Read the existing `~/.claude/settings.json`. If it has no `"hooks"` key, add the entire block below. If it already has `"hooks"`, **merge** — do NOT overwrite existing hook entries.

Target `settings.json` must contain:

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

**Notes**:
- Use `pythonw` (not `python`) to prevent console window flash.
- `~` is expanded by Claude Code automatically; keep it as `~`.

### Step 4: Verify

Run these checks:

1. All 4 `.pyw` files exist in `~/.claude/hooks/scripts/`
2. `pythonw --version` returns Python 3.10+
3. `pythonw -c "import tkinter; print('ok')"` prints `ok`
4. `~/.claude/settings.json` is valid JSON
5. `hooks.PermissionRequest`, `hooks.PreToolUse`, `hooks.Stop` all present in settings

### Step 5: Report

Tell the user:
- Which files were downloaded
- Whether settings.json was created new or merged
- Any warnings (e.g. tkinter unavailable, old hooks overwritten)
- They must **restart Claude Code session** for hooks to take effect

## Troubleshooting

- **Console flash**: `command` must use `pythonw`, not `python`
- **No dialog**: `pythonw -c "import tkinter"` fails → tkinter not installed
- **Hooks not triggering**: Restart Claude Code — hooks load at session start
- **OSC 9 notification not showing**: Needs modern terminal (Windows Terminal / WezTerm); legacy cmd.exe does not support OSC 9
