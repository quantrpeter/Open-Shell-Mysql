"""Session password is sealed at rest. Run: python command/test_session_seal.py"""

from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
from pathlib import Path

from cryptography.fernet import Fernet

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent.parent / "Open-Shell"))

import client  # noqa: E402
from openshell import ENV, ShellError  # noqa: E402


def fail(message: str) -> None:
	raise SystemExit(message)


def main() -> None:
	key = Fernet.generate_key().decode()
	other = Fernet.generate_key().decode()
	password = "secret!@#"
	with tempfile.TemporaryDirectory() as home:
		os.environ["HOME"] = home
		os.environ[client.SESSION_KEY_NAME] = key
		ENV.clear()
		session = {
			"host": "127.0.0.1",
			"port": 3306,
			"user": "root",
			"password": password,
			"database": "app",
		}
		client.save_session(session)
		if session["password"] != password:
			fail("save_session mutated the caller password")
		path = client.session_path()
		mode = stat.S_IMODE(path.stat().st_mode)
		if mode != 0o600:
			fail(f"session mode {oct(mode)}, want 0o600")
		raw = path.read_text(encoding="utf-8")
		if password in raw:
			fail("plaintext password written to session.json")
		stored = json.loads(raw)
		envelope = stored["password"]
		if not isinstance(envelope, dict) or envelope.get("$t") != "oshell.secret":
			fail(f"password was not sealed: {envelope!r}")
		loaded = client.load_session()
		if loaded["password"] != password:
			fail("load_session did not return the password")
		if password in path.read_text(encoding="utf-8"):
			fail("load_session wrote the password back in plaintext")

		legacy = dict(stored)
		legacy["password"] = password
		path.write_text(json.dumps(legacy) + "\n", encoding="utf-8")
		migrated = client.load_session()
		if migrated["password"] != password:
			fail("legacy password was not accepted")
		resealed = json.loads(path.read_text(encoding="utf-8"))["password"]
		if not isinstance(resealed, dict) or resealed.get("$t") != "oshell.secret":
			fail("legacy session was not resealed")

		del os.environ[client.SESSION_KEY_NAME]
		try:
			client.save_session({"host": "127.0.0.1", "password": "other-secret"})
		except ShellError as err:
			if err.code != "mysql.no_session_key":
				fail(f"missing key raised {err.code}")
		else:
			fail("missing key wrote a session")
		if "other-secret" in path.read_text(encoding="utf-8"):
			fail("missing key changed the session file")

		os.environ[client.SESSION_KEY_NAME] = other
		try:
			client.load_session()
		except ShellError as err:
			if err.code != "mysql.bad_session":
				fail(f"wrong key raised {err.code}")
		else:
			fail("wrong key did not fail")
		os.environ[client.SESSION_KEY_NAME] = key
		empty = dict(session)
		empty["password"] = ""
		client.save_session(empty)
		if json.loads(path.read_text(encoding="utf-8"))["password"] is not None:
			fail("empty password was not stored as null")
		lines = client.client_config(empty)
		if any(line.startswith("password=") for line in lines):
			fail("empty password was added to the client config")
		secret_lines = client.client_config(session)
		if f"password={client.cnf_value(password)}" not in secret_lines:
			fail("plaintext password missing from client config")
	print("ok")


if __name__ == "__main__":
	main()
