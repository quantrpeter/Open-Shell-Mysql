"""Shared MySQL session and client helpers. Not a command."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from openshell import ENV, ShellError, user_package_dir

PACKAGE = "mysql"
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 3306
DEFAULT_USER = "root"


def session_path() -> Path:
	return user_package_dir() / PACKAGE / "session.json"


def setting(*names: str) -> str:
	for name in names:
		value = ENV.get(name)
		if value is None:
			continue
		text = str(value).strip()
		if text:
			return text
	return ""


def int_setting(name: str, default: int) -> int:
	value = ENV.get(name)
	if value is None or value == "":
		return default
	try:
		return int(value)
	except (TypeError, ValueError) as err:
		raise ShellError("arg.bad", f"mysql: bad {name} {value!r}",
						 "use an integer port, e.g. 3306") from err


def cnf_value(value: str | int) -> str:
	"""Quote a MySQL option-file value so `#`, `!`, and `;` stay literal."""
	text = str(value).replace("\\", "\\\\").replace('"', '\\"')
	return f'"{text}"'


def mysql_client() -> str:
	client = shutil.which("mysql")
	if client is None:
		raise ShellError("mysql.no_client", "mysql client not found on PATH",
						 "install the MySQL or MariaDB client")
	return client


def load_session() -> dict:
	path = session_path()
	if not path.is_file():
		raise ShellError("mysql.not_connected", "no MySQL session",
						 "run `mysql:connect` first")
	try:
		data = json.loads(path.read_text(encoding="utf-8"))
	except json.JSONDecodeError as err:
		raise ShellError("mysql.bad_session", f"invalid session file: {err}",
						 "run `mysql:connect` again") from err
	except OSError as err:
		raise ShellError("mysql.bad_session", f"cannot read session: {err}",
						 "run `mysql:connect` again") from err
	if not isinstance(data, dict):
		raise ShellError("mysql.bad_session", "session file is not an object",
						 "run `mysql:connect` again")
	return data


def save_session(session: dict) -> None:
	path = session_path()
	path.parent.mkdir(parents=True, exist_ok=True)
	path.write_text(json.dumps(session, indent=2) + "\n", encoding="utf-8")


def run_mysql(session: dict, sql: str) -> subprocess.CompletedProcess[str]:
	client = mysql_client()
	host = session.get("host") or DEFAULT_HOST
	user = session.get("user") or DEFAULT_USER
	password = session.get("password") or ""
	database = session.get("database") or ""
	port = session.get("port") or DEFAULT_PORT
	config = [
		"[client]",
		f"host={cnf_value(host)}",
		f"port={cnf_value(port)}",
		f"user={cnf_value(user)}",
		"connect-timeout=5",
		"default-character-set=utf8mb4",
	]
	if password:
		config.append(f"password={cnf_value(password)}")
	if database:
		config.append(f"database={cnf_value(database)}")

	with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".cnf", delete=False) as handle:
		handle.write("\n".join(config) + "\n")
		cnf = Path(handle.name)
	os.chmod(cnf, 0o600)
	try:
		return subprocess.run(
			[
				client,
				f"--defaults-extra-file={cnf}",
				"--batch",
				"--raw",
				"--default-character-set=utf8mb4",
				"-e", sql,
			],
			check=False,
			capture_output=True,
			text=True,
		)
	except OSError as err:
		raise ShellError("mysql.exec_failed", f"cannot run mysql: {err}",
						 "install the MySQL client") from err
	finally:
		cnf.unlink(missing_ok=True)


def cell_value(text: str):
	if text == "\\N":
		return None
	if text == "":
		return ""
	if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
		try:
			return int(text)
		except ValueError:
			return text
	if text.count(".") == 1:
		left, right = text.split(".", 1)
		if (left.isdigit() or (left.startswith("-") and left[1:].isdigit())) and right.isdigit():
			try:
				return float(text)
			except ValueError:
				return text
	return text


def records_from_batch(text: str):
	body = text.replace("\r\n", "\n").strip("\n")
	if not body.strip():
		return
	lines = body.split("\n")
	headers = lines[0].split("\t")
	for line in lines[1:]:
		parts = line.split("\t")
		yield {
			headers[i]: cell_value(parts[i]) if i < len(parts) else None
			for i in range(len(headers))
		}


# Loaded as a command file; keep the package dir importable for siblings.
_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
	sys.path.insert(0, _HERE)
