"""mysql:connect - open a MySQL connection and remember it."""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from openshell import SETTINGS, Records, ShellError, command, parse_args, user_package_dir

PACKAGE = "mysql"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 3306
DEFAULT_USER = "root"


def _session_path():
	return user_package_dir() / PACKAGE / "session.json"


def _setting(*names: str) -> str:
	for name in names:
		value = SETTINGS.get(name)
		if value is None:
			continue
		text = str(value).strip()
		if text:
			return text
	return ""


def _int_setting(name: str, default: int) -> int:
	value = SETTINGS.get(name)
	if value is None or value == "":
		return default
	try:
		return int(value)
	except (TypeError, ValueError) as err:
		raise ShellError("arg.bad", f"mysql:connect: bad {name} {value!r}",
						 "use an integer port, e.g. 3306") from err


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

	host = paths[0] if paths else _setting("mysql_host", "mysql.host") or DEFAULT_HOST
	user = opts.get("user") or _setting("mysql_user", "mysql.user") or DEFAULT_USER
	password = opts.get("password")
	print(password)
	if password is None:
		password = _setting("mysql_password", "mysql.password")
	database = opts.get("database") or _setting("mysql_database", "mysql.database")
	if "port" in opts:
		try:
			port = int(opts["port"])
		except ValueError as err:
			raise ShellError("arg.bad", f"mysql:connect: bad port {opts['port']!r}",
							 "pass an integer, e.g. mysql:connect -P 3306") from err
	else:
		port = _int_setting("mysql_port", DEFAULT_PORT)

	client = shutil.which("mysql")
	if client is None:
		raise ShellError("mysql.no_client", "mysql client not found on PATH",
						 "install the MySQL or MariaDB client")

	config = [
		"[client]",
		f"host={host}",
		f"port={port}",
		f"user={user}",
		"connect-timeout=5",
	]
	if password:
		config.append(f"password={password}")
	if database:
		config.append(f"database={database}")

	with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".cnf", delete=False) as handle:
		handle.write("\n".join(config) + "\n")
		cnf = Path(handle.name)
	try:
		completed = subprocess.run(
			[client, f"--defaults-extra-file={cnf}", "--batch", "--raw", "-e", "SELECT 1 AS ok"],
			check=False,
			capture_output=True,
			text=True,
		)
	except OSError as err:
		raise ShellError("mysql.connect_failed", f"cannot run mysql: {err}",
						 "install the MySQL client") from err
	finally:
		cnf.unlink(missing_ok=True)
	if completed.returncode != 0:
		message = (completed.stderr or completed.stdout or "connection failed").strip()
		raise ShellError("mysql.connect_failed", message,
						 "check host, user, password, and that mysqld is running")

	session = {
		"host": host,
		"port": port,
		"user": user,
		"password": password,
		"database": database,
	}
	path = _session_path()
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(json.dumps(session, indent=2) + "\n", encoding="utf-8")

	yield {
		"ok": True,
		"host": host,
		"port": port,
		"user": user,
		"database": database or None,
		"client": client,
	}
