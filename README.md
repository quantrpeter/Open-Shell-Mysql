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

Requires the `mysql` CLI on `PATH` (MySQL or MariaDB client).

## Commands

| Command | Usage | What it does |
|---|---|---|
| `mysql:connect` | `mysql:connect [HOST] [-u USER] [-p PASS] [-P PORT] [-D DATABASE]` | Open a MySQL connection and remember it |
| `mysql:session` | `mysql:session` | Dump the saved session (`host`, `port`, `user`, `password`, `database`) |
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

Later MySQL commands in this package will reuse that session.

## Settings

Connection defaults can live in `~/.openshell`:

```json
{
  "mysql_host": "127.0.0.1",
  "mysql_port": 3306,
  "mysql_user": "root",
  "mysql_password": "",
  "mysql_database": ""
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
