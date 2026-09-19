"""mysql:sql - run SQL on the saved MySQL session."""

from __future__ import annotations

import sys
from pathlib import Path

from openshell import Records, ShellError, command

_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
	sys.path.insert(0, _HERE)

from client import load_session, records_from_batch, run_mysql  # noqa: E402


@command("mysql:sql", "Run SQL on the saved MySQL session", "mysql:sql SQL …",
		 source=True)
def mysql_sql(_input: Records, args: list[str]) -> Records:
	sql = " ".join(args).strip().rstrip(";")
	if not sql:
		raise ShellError("arg.missing", "mysql:sql: SQL required",
						 'e.g. mysql:sql select * from users')
	completed = run_mysql(load_session(), sql)
	if completed.returncode != 0:
		message = (completed.stderr or completed.stdout or "query failed").strip()
		raise ShellError("mysql.sql_failed", message,
						 "check the SQL and that `mysql:connect` succeeded")
	rows = list(records_from_batch(completed.stdout or ""))
	if rows:
		yield from rows
		return
	yield {"ok": True}
