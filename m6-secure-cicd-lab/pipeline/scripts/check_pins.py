#!/usr/bin/env python3
"""check_pins.py REQUIREMENTS — every dependency must be pinned to an exact version. Exit 1 otherwise.

A range pin (>=, ~=, *) means today's reproducible build is not tomorrow's. A pin is the floor of supply-chain
hygiene; --require-hashes is the ceiling, and is out of scope here because hash files are platform-specific.
"""
import re
import sys

EXACT = re.compile(r"^[A-Za-z0-9_.\-]+==[0-9][^;]*$")


def check(path):
    bad = []
    for raw in open(path):
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        if not EXACT.match(line):
            bad.append(line)
    return bad


if __name__ == "__main__":
    req = sys.argv[1] if len(sys.argv) > 1 else "requirements.txt"
    bad = check(req)
    if not bad:
        print(f"all dependencies in {req} are pinned to an exact version — exit 0")
        sys.exit(0)
    for b in bad:
        print(f"  [FINDING] not an exact pin: {b!r}  (a range means the build is not reproducible)")
    sys.exit(1)
