"""Reject native hosts whose compiled display controls are missing."""
from pathlib import Path


def verify(library, require_dual=False):
    data = Path(library).read_bytes()
    dual_backend = any(marker in data for marker in (
        b'RetunedDualScreen_surface', b'RetunedAttachDuoGameView'))
    if require_dual or dual_backend:
        missing = [label for label in ('Screen mode', 'Bottom equipment panel')
                   if label.encode() + b'\0' not in data]
        if missing:
            raise ValueError('Compiled display settings missing: ' + ', '.join(missing))
    return {'dual_backend_detected': dual_backend, 'display_controls': 'PASS'}
