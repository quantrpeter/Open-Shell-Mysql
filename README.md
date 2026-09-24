# Open Shell MySQL

Command package for [Open Shell](https://github.com/quantrpeter/Open-Shell).
Commands use the `package:command` convention. This package is `mysql`.

## Install

From GitHub:

```bash
openshell -c 'install https://github.com/quantrpeter/Open-Shell-Mysql'
```

From a local checkout of this repo:

```bash
openshell -c 'install .'
# or:  openshell -c 'install /path/to/Open-Shell-Mysql'
```

`install` copies `command/*.py` into `~/.config/oshell/package/mysql/` and
prints a record:

| Field | Meaning |
|---|---|
| `name` | Package name (`Open-Shell-Mysql` → `mysql`) |
| `path` | Local folder the files were copied into |
| `files` | Command files that were installed |
| `source` | GitHub URL or local folder you installed from |
| `status` | `installed` |
| `kind` | `package` (not a website extra) |
| `branch` | Git branch used (`main` for GitHub installs) |

Then:

```bash
openshell -c 'mysql:connect'
openshell -c 'help mysql:connect'
```

After a local `install ../Open-Shell-Mysql`, `reload` recopies `command/*.py`
from that checkout. You do not need to install again after editing.

Requires the `mysql` CLI on `PATH` (MySQL or MariaDB client) and the
`cryptography` package (`pip install cryptography`). The session password is
sealed with Fernet before it is written to disk.

## Commands

| Command | Usage | What it does |
|---|---|---|
| `mysql:connect` | `mysql:connect [HOST] [-u USER] [-p PASS] [-P PORT] [-D DATABASE]` | Open a MySQL connection and remember it |
| `mysql:session` | `mysql:session` | Dump the saved session (`host`, `port`, `user`, `database`). The password is not printed |
| `mysql:sql` | `mysql:sql SQL …` | Run SQL on the saved session; each row is a record |

Examples:

```bash
mysql:connect
mysql:connect -u root -p 'secret!@#'
mysql:connect 127.0.0.1 -u root -p secret -P 3306 -D app
mysql:session
mysql:sql select * from users
mysql:sql "select id, name from users where id = 1"
mysql:sql select * from users | take 5
```

A successful connect stores the session at:

```text
~/.config/oshell/package/mysql/session.json
```

The `password` field in that file is a Fernet envelope, not the secret. The
file is mode `0600`. Later MySQL commands in this package unseal it in memory.

Set the key before `mysql:connect`. Process environment wins over `~/.openshell`:

```bash
export mysql_session_key="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
```

Or, less safely, `set mysql_session_key <fernet-key>` (that file is plain text
and `env` prints it). An older session file that still has a plain password is
accepted once and rewritten sealed.

## Settings

Connection defaults can live in `~/.openshell`:

```json
{
  "mysql_host": "127.0.0.1",
  "mysql_port": 3306,
  "mysql_user": "root",
  "mysqlsession.py    mysql:session
command/cdatabase": ""
}
```

Flags on `mysql:connect` override these settings.

## Layout

```text
command/client.py     shared session / mysql CLI helpers
command/cession.py    mysql:session
command/sonnect.py    mysql:connect
command/sql.py        mysql:sql
README.md
```

The decorator is the command name (`mysql:connect`), not the filename.
