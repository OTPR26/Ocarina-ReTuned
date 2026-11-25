"""Reject modified or incomplete generator dependencies before compiling."""
import hashlib
import json
from pathlib import Path
import sys
from fetch_source import REVISION
root = Path(sys.argv[1])
receipt = json.loads((root / 'source-receipt.json').read_text())
if receipt['revision'] != REVISION:
    raise SystemExit('Unexpected generator source revision')
for name, expected in receipt['files'].items():
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise SystemExit('Generator source mismatch: ' + name)
