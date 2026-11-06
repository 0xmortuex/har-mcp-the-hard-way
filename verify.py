"""Run every module's main.py in a child process, the way CI does.

Each main.py checks its own results with assert, so a chapter whose code drifts out of sync
with what its README claims fails here.

Usage: python verify.py            # all modules
       python verify.py 02 04      # just these
       python verify.py --big      # also run module 07 with the 100 MB file
"""

from __future__ import annotations

import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))


def modules(only: list[str]) -> list[str]:
    found = sorted(d for d in os.listdir(ROOT) if d[:2].isdigit() and os.path.isfile(os.path.join(ROOT, d, "main.py")))
    return [d for d in found if not only or d[:2] in only]


def main() -> int:
    args = sys.argv[1:]
    big = "--big" in args
    only = [a for a in args if not a.startswith("--")]
    # Windows consoles default to cp1252 and crash on non-ASCII output; force UTF-8 in children.
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    failed = []
    for d in modules(only):
        cmd = [sys.executable, os.path.join(ROOT, d, "main.py")] + (["--big"] if big and d.startswith("07") else [])
        t = time.perf_counter()
        proc = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", timeout=900)
        ok = proc.returncode == 0 and f"module {d[:2]} ok" in proc.stdout
        print(f"{'PASS' if ok else 'FAIL'}  {d}  ({time.perf_counter() - t:.1f}s)")
        if not ok:
            failed.append(d)
            print(proc.stdout[-2000:])
            print(proc.stderr[-3000:])
    if failed:
        print(f"\n{len(failed)} module(s) failed: {', '.join(failed)}")
        return 1
    print("\nall modules verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
