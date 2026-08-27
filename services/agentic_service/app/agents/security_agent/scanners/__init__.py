"""Public scanner API.

The scanner implementation lives in the sibling ``scanners.py`` module while
this directory contains scanner-specific helpers.  Since Python resolves this
package before the sibling module, re-export the implementation explicitly so
existing imports keep working.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


_IMPLEMENTATION_PATH = Path(__file__).resolve().parent.parent / "scanners.py"
_SPEC = importlib.util.spec_from_file_location(
	"app.agents.security_agent._scanner_implementation",
	_IMPLEMENTATION_PATH,
)
if _SPEC is None or _SPEC.loader is None:
	raise ImportError(f"Unable to load scanner implementation from {_IMPLEMENTATION_PATH}")

_IMPLEMENTATION = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_IMPLEMENTATION)

list_scannable_files = _IMPLEMENTATION.list_scannable_files
scan_dangerous_patterns = _IMPLEMENTATION.scan_dangerous_patterns
scan_dependencies = _IMPLEMENTATION.scan_dependencies
scan_secrets = _IMPLEMENTATION.scan_secrets

__all__ = [
	"list_scannable_files",
	"scan_dangerous_patterns",
	"scan_dependencies",
	"scan_secrets",
]
