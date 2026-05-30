# Claude Code Hooks for Windows

Native Windows GUI hooks for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) — zero external dependencies, powered by Python + tkinter.

> [!NOTE]
> Claude Code hooks are user-defined scripts that execute automatically at specific points in Claude Code's lifecycle. See the [official hooks reference](https://docs.anthropic.com/en/docs/claude-code/hooks) for details.

## Features

| Hook | Event | What it does |
|------|-------|--------------|
| **Permission Request** | `PermissionRequest` | Shows a native Allow/Deny dialog with suggestion buttons (session/project/global scope) |
| **Ask User Question** | `PreToolUse` → `AskUserQuestion` | Renders question options as native Radiobutton (single select) or Checkbutton (multi select) dialogs |
| **Stop Notify** | `Stop` | Sends an OSC 9 terminal notification when Claude finishes responding |
| **Exit Plan Mode** | `PermissionRequest` → `ExitPlanMode` | Shows a topmost messagebox when a plan is ready for review (auto-closes after 25s) |

### Highlights

- **Zero dependencies** — only Python 3.10+ and tkinter (bundled with Python on Windows)
- **Native Windows look** — uses system default widgets, no custom theming
- **Keyboard friendly** — Enter to Allow/Confirm, Escape to Deny/Cancel, number keys for suggestions
- **Scrollable content** — long commands and text wrap and scroll naturally
- **`.pyw` suffix** — no console window flash on launch

## Prerequisites

- Windows 10/11
- Python 3.10+ with tkinter (included in standard CPython installer)
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed and configured

## Quick Start (One-Click AI Install)

Copy the entire content of [`AI_SETUP_GUIDE.md`](AI_SETUP_GUIDE.md) and paste it to your AI assistant (Claude Code, ChatGPT, etc.), then say "帮我安装". The AI will automatically create all files, configure settings.json, and verify the setup. No manual steps needed.

## Manual Installation

### 1. Clone this repo

```bash
git clone https://github.com/YOUR_USERNAME/claude-code-hooks.git
cd claude-code-hooks
```

### 2. Configure Claude Code

Edit your global settings file at `~/.claude/settings.json` (create it if it doesn't exist), and add the hooks configuration:

```json
{
  "hooks": {
    "PermissionRequest": [
      {
        "matcher": "Bash|Edit|Write|Read|Glob|Grep|WebFetch|WebSearch|mcp__.*",
        "hooks": [
          {
            "type": "command",
            "command": "pythonw ${CLAUDE_PROJECT_DIR}/hooks/permission_request.pyw"
          }
        ]
      },
      {
        "matcher": "ExitPlanMode",
        "hooks": [
          {
            "type": "command",
            "command": "pythonw ${CLAUDE_PROJECT_DIR}/hooks/exit_plan_mode_notify.pyw"
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
            "command": "pythonw ${CLAUDE_PROJECT_DIR}/hooks/ask_user_question.pyw"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "pythonw ${CLAUDE_PROJECT_DIR}/hooks/stop_notify.pyw"
          }
        ]
      }
    ]
  }
}
```

> [!TIP]
> Replace `${CLAUDE_PROJECT_DIR}` with the absolute path to this repo if you want global hooks, or keep the variable to use it as a project-level hook.

> [!IMPORTANT]
> Use `pythonw` (not `python`) to launch `.pyw` files — this prevents a console window from flashing on screen.

### 3. Restart Claude Code

Hooks are loaded when a session starts. Restart your Claude Code session for changes to take effect.

## Hook Details

### Permission Request (`permission_request.pyw`)

Intercepts `PermissionRequest` events and shows a dialog with:

- **Tool name** and **action summary** (e.g. "Bash Command", "Edit File")
- **Scrollable content area** for long commands or file paths
- **Allow / Deny** buttons (Enter / Escape keyboard shortcuts)
- **Suggestion buttons** when Claude provides permission suggestions:
  - "Allow for Session" / "Always Allow (Project)" / "Always Allow (Global)"
  - "Deny for Session" / "Always Deny (Project)" / "Always Deny (Global)"
  - "Auto Approve (Session)" / "Auto Approve (Project)"
  - "Plan Mode (Session)"

**Matcher regex**: `Bash|Edit|Write|Read|Glob|Grep|WebFetch|WebSearch|mcp__.*`

This covers all tools that typically require permission. Adjust as needed.

### Ask User Question (`ask_user_question.pyw`)

Intercepts `PreToolUse` events for the `AskUserQuestion` tool and renders a native dialog with:

- **Header chips** for each question category
- **Single select** → Checkbutton with mutual exclusion (radio-like behavior)
- **Multi select** → Checkbutton with independent toggles
- **Option descriptions** displayed below each option
- **Confirm / Cancel** buttons
- **Scrollable** for many questions/options

The output conforms to Claude Code's `PreToolUse` spec: echoes back the original `questions` array and adds an `answers` dict.

### Stop Notify (`stop_notify.pyw`)

Fires when Claude finishes responding. Emits an **OSC 9 terminal notification sequence**:

```
\033]9;Claude Code;Task completed\007
```

This triggers a desktop notification in Windows Terminal, iTerm2, WezTerm, ConEmu, and other modern terminals.

> [!NOTE]
> This is a cross-platform approach. It works on any terminal that supports OSC 9. No WinRT or system APIs required.

### Exit Plan Mode (`exit_plan_mode_notify.pyw`)

Fires when `ExitPlanMode` is triggered (routed via `PermissionRequest` matcher). Shows a **topmost messagebox** that:

- Stays on top of all windows
- Auto-closes after 25 seconds
- Alerts you that a plan is ready for review

## Project Structure

```
claude-code-hooks/
├── hooks/
│   ├── permission_request.pyw     # Allow/Deny dialog with suggestions
│   ├── ask_user_question.pyw      # Question option dialog
│   ├── stop_notify.pyw            # OSC 9 terminal notification
│   └── exit_plan_mode_notify.pyw  # Plan-ready messagebox
├── examples/
│   └── settings.json              # Full settings.json example
├── AI_SETUP_GUIDE.md              # One-click AI install guide
├── claude-hooks-reference.md      # Official hooks reference (offline copy)
├── LICENSE
└── README.md
```

## Known Limitations

- **Windows only** — tkinter dialogs are Windows-native. macOS and Linux users would need to adapt the scripts or use alternative approaches.
- **No dark mode** — tkinter uses system default styling. No custom theming is applied.
- **Stop notify requires a modern terminal** — OSC 9 sequences only work in Windows Terminal, WezTerm, etc. The legacy `cmd.exe` and basic PowerShell console do not support them.
- **No async notification** — The Stop hook uses `terminalSequence` (synchronous output). It does not use the `async` field for background notifications.

## FAQ

### Why `.pyw` files?

The `.pyw` extension tells Windows to run the script with `pythonw.exe`, which does not create a console window. Without this, every hook invocation would flash a black cmd window.

### Why not use PowerShell Toast notifications?

PowerShell WinRT Toast notifications work well when called directly, but **fail silently when invoked from a subprocess** (which is exactly how Claude Code hooks run). The OSC 9 terminal sequence is more reliable in this context.

### Can I use these hooks with other Claude Code clients?

These hooks are designed for the Claude Code CLI. Other clients (like Claude Desktop or IDE extensions) may not support the hooks system.

### How do I debug a hook?

Run the script manually with sample JSON input:

```bash
echo '{"tool_name":"Bash","tool_input":{"command":"ls -la"},"permission_suggestions":[]}' | python hooks/permission_request.pyw
```

## Contributing

Contributions are welcome! Areas of particular interest:

- macOS/Linux compatibility
- Additional hook implementations (PostToolUse, SessionStart, etc.)
- Bug fixes and improvements

Please open an issue first to discuss what you would like to change.

## License

[MIT](LICENSE)
