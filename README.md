# Open Shell MySQL

Command package for [Open Shell](https://github.com/quantrpeter/Open-Shell).
Install from GitHub:

```bash
openshell -c 'install https://github.com/quantrpeter/Open-Shell-Mysql'
openshell -c 'mysql:connect'
```

Or from a local checkout:

```bash
openshell -c 'install /Users/peter/workspace/Open-Shell-Mysql'
```

Commands use the `package:command` convention. This package is `mysql`.

| Command | Usage | What it does |
|---|---|---|
| `mysql:connect` | `mysql:connect [HOST] [-u USER] [-p PASS] [-P PORT] [-D DATABASE]` | Open a MySQL connection and store it for later commands |

Connection settings can also live in `~/.openshell`:

```json
{
  "mysql_host": "127.0.0.1",
  "mysql_port": 3306,
  "mysql_user": "root",
  "mysql_password": "",
  "mysql_database": ""
}
```

Requires the `mysql` CLI on `PATH` (MySQL or MariaDB client).
