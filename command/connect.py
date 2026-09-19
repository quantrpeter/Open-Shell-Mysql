"""mysql:connect - open a MySQL connection and remember it."""

from __future__ import annotations

import sys
from pathlib import Path

from openshell import Records, ShellError, command, parse_args

_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
	sys.path.insert(0, _HERE)

from client import (  # noqa: E402
	DEFAULT_HOST, DEFAULT_PORT, DEFAULT_USER,
	int_setting, mysql_client, run_mysql, save_session, setting,
)


@command(
	"mysql:connect",
	"Connect to a MySQL server",
	"mysql:connect [HOST] [-u USER] [-p PASS] [-P PORT] [-D DATABASE]",
	source=True,
)
def mysql_connect(_input: Records, args: list[str]) -> Records:
	_flags, opts, paths = parse_args(
		args, "mysql:connect",
		valued={
			"-u": "user", "--user": "user",
			"-p": "password", "--password": "password",
			"-P": "port", "--port": "port",
			"-D": "database", "--database": "database",
		},
	)
	if len(paths) > 1:
		raise ShellError("arg.bad", "mysql:connect: extra arguments",
						 "e.g. mysql:connect 127.0.0.1 -u root -D app")

	host = paths[0] if paths else setting("mysql_host", "mysql.host") or DEFAULT_HOST
	user = opts.get("user") or setting("mysql_user", "mysql.user") or DEFAULT_USER
	password = opts.get("password")
	if password is None:
		password = setting("mysql_password", "mysql.password")
	database = opts.get("database") or setting("mysql_database", "mysql.database")
	if "port" in opts:
		try:
			port = int(opts["port"])
		except ValueError as err:
			raise ShellError("arg.bad", f"mysql:connect: bad port {opts['port']!r}",
							 "pass an integer, e.g. mysql:connect -P 3306") from err
	else:
		port = int_setting("mysql_port", DEFAULT_PORT)

	session = {
		"host": host,
		"port": port,
		"user": user,
		"password": password,
		"database": database,
	}
	completed = run_mysql(session, "SELECT 1 AS ok")
	if completed.returncode != 0:
		message = (completed.stderr or completed.stdout or "connection failed").strip()
		raise ShellError("mysql.connect_failed", message,
						 "check host, user, password, and that mysqld is running")

	save_session(session)
	yield {
		"ok": True,
		"host": host,
		"port": port,
		"user": user,
		"database": database or None,
		"client": mysql_client(),
	}

