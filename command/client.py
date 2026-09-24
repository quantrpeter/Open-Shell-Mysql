"""Shared MySQL session and client helpers. Not a command."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from openshell import ENV, ShellError, user_package_dir

PACKAGE = "mysql"
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 3306
DEFAULT_USER = "root"
SESSION_KEY_NAME = "mysql_session_key"
SECRET_TYPE = "oshell.secret"
SECRET_VERSION = 1
_KEY_HINT = (
	'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
)


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


def session_key() -> str:
	"""Fernet key from the process env, else `~/.openshell`."""
	raw = os.environ.get(SESSION_KEY_NAME, "").strip() or setting(SESSION_KEY_NAME)
	if not raw:
		raise ShellError(
			"mysql.no_session_key",
			f"{SESSION_KEY_NAME} is not set",
			f"export {SESSION_KEY_NAME}=<fernet-key> or `set {SESSION_KEY_NAME} <fernet-key>`",
		)
	try:
		Fernet(raw.encode("ascii"))
	except (UnicodeEncodeError, ValueError, TypeError) as err:
		raise ShellError(
			"mysql.bad_session_key",
			f"{SESSION_KEY_NAME} is not a Fernet key",
			f"generate one with {_KEY_HINT}",
		) from err
	return raw


def seal_password(password: str) -> dict:
	"""Return a Fernet envelope. Caller must not pass an empty password."""
	token = Fernet(session_key().encode("ascii")).encrypt(password.encode("utf-8"))
	return {
		"$t": SECRET_TYPE,
		"v": SECRET_VERSION,
		"alg": "fernet",
		"ct": token.decode("ascii"),
	}


def open_password(value) -> str | None:
	"""Return a plaintext password from a legacy string, null, or envelope."""
	if value is None:
		return None
	if value == "":
		return ""
	if isinstance(value, str):
		return value
	if not isinstance(value, dict) or value.get("$t") != SECRET_TYPE:
		raise ShellError("mysql.bad_session", "session password is not sealed",
						 "run `mysql:connect` again")
	if value.get("v") != SECRET_VERSION or value.get("alg") != "fernet":
		raise ShellError("mysql.bad_session", "unsupported session password seal",
						 "run `mysql:connect` again")
	token = value.get("ct")
	if not isinstance(token, str) or not token:
		raise ShellError("mysql.bad_session", "session password seal is empty",
						 "run `mysql:connect` again")
	try:
		plain = Fernet(session_key().encode("ascii")).decrypt(token.encode("ascii"))
	except (InvalidToken, ValueError, TypeError, UnicodeError) as err:
		raise ShellError("mysql.bad_session", "cannot unseal session password",
						 "check mysql_session_key, or run `mysql:connect` again") from err
	return plain.decode("utf-8")


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
	stored = data.get("password")
	data["password"] = open_password(stored)
	if isinstance(stored, str) and stored:
		save_session(data)
	return data


def save_session(session: dict) -> None:
	path = session_path()
	parent = path.parent
	created = not parent.exists()
	parent.mkdir(parents=True, exist_ok=True)
	if created:
		os.chmod(parent, 0o700)
	stored = dict(session)
	password = stored.get("password")
	if isinstance(password, str) and password:
		stored["password"] = seal_password(password)
	elif password == "":
		stored["password"] = None
	text = json.dumps(stored, indent=2) + "\n"
	tmp = path.with_suffix(".json.tmp")
	try:
		tmp.write_text(text, encoding="utf-8")
		os.chmod(tmp, 0o600)
		os.replace(tmp, path)
	except OSError as err:
		tmp.unlink(missing_ok=True)
		raise ShellError("mysql.bad_session", f"cannot write session: {err}",
						 "check permissions on ~/.config/oshell/package/mysql") from err
	os.chmod(path, 0o600)


def client_config(session: dict) -> list[str]:
	"""MySQL option-file lines. Empty passwords are omitted."""
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
	return config


def run_mysql(session: dict, sql: str) -> subprocess.CompletedProcess[str]:
	client = mysql_client()
	config = client_config(session)

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
