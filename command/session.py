"""mysql:session - dump the saved MySQL session."""

from __future__ import annotations

import sys
from pathlib import Path

from openshell import Records, command

_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
	sys.path.insert(0, _HERE)

from client import load_session, session_path  # noqa: E402


@command("mysql:session", "Dump the saved MySQL session", "mysql:session",
		 source=True)
def mysql_session(_input: Records, _args: list[str]) -> Records:
	session = load_session()
	yield {
		"host": session.get("host"),
		"port": session.get("port"),
		"user": session.get("user"),
		"database": session.get("database") or None,
		"path": str(session_path()),
	}
