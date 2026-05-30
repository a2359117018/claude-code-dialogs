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
