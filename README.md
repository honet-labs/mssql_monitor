# Microsoft SQL Server Monitoring for Pandora FMS

> **Version:** 1.0.1  
> **Platform:** Pandora FMS Discovery (Application)  
> **Package:** `pandorafms.mssql_monitor.disco`  
> **Status:** Community-maintained integration; test on your target versions before production use.

## Overview

A community-developed Pandora FMS Discovery extension for Microsoft SQL Server monitoring, with DMV-based session/performance modules and user-defined read-only T-SQL modules.

This repository contains a **Pandora FMS Discovery application**, not a Microsoft SQL Server installation and not a standalone Pandora agent. Monitoring runs remotely from the Pandora Discovery server and generates XML data modules ingested by Pandora FMS.

## Features

- **18 built-in SQL monitoring modules**, organized by group and individually enabled/disabled at group level.
- Up to **10 user-defined SQL modules per Discovery task**, entered via separate UI fields (name, type, unit, group, result mode and multiline query).
- Numeric and text modules, including a **readable multi-row/multi-column table** for Pandora snapshot views.
- Collector self-monitoring (connection status, query/error counters and collection time).
- **At most one database connection per execution**, with sequential SQL execution and per-task local overlap locking.
- Single-statement `SELECT`/`WITH` safety checking, query timeout controls, run logs, and per-task configuration supplied by Pandora.

## How it works

```text
Pandora Console (Discovery task wizard)
                 |
       discovery_definition.ini
                 |
        Python SQL collector
                 |
      1 database connection
                 |
        built-in + custom SQL
                 |
       Pandora XML .data file
                 |
        Pandora Data Server
                 |
        Agent / monitoring modules
```

## Requirements

- **Pandora FMS** with the Discovery Applications feature enabled (developed against the Pandora FMS 8.0NG.805 workflow; other versions not guaranteed).
- **Linux Pandora Discovery server** with `/usr/bin/python3` (the path invoked by this package).
- **Python driver:** `pyodbc` **plus a system ODBC driver** (`ODBC Driver 18 for SQL Server`, `ODBC Driver 17 for SQL Server`, or FreeTDS).
- **Database/network:** SQL Server TCP access (default `1433`), SQL Authentication login, selected database (default `master`), ODBC driver selection, and TLS options. The default is encryption enabled and server-certificate trust disabled.
- Write permission to Pandora incoming directory (provided as `__incomingDir__`) and to the configured run-log location.
- Linux `flock` support, used to suppress overlapping executions on the **same host/task**.

### Install and verify the driver

Install a supported ODBC driver and unixODBC first, following the Microsoft instructions for your Linux distribution. Then install `pyodbc` into the **same** `/usr/bin/python3` environment used by Pandora Discovery (for example, `python3 -m pip install pyodbc` where policy permits).

```bash
/usr/bin/python3 -c "import pyodbc; print(pyodbc.drivers())"
```

List installed system ODBC drivers as well:

```bash
odbcinst -q -d
```

**Important:** Installing a driver into a virtual environment or `root` user environment does not automatically make it available to the system Python executable `/usr/bin/python3` or the service account running Discovery. Match the interpreter, package location, and filesystem permissions.

## Installation in Pandora FMS

1. Obtain `pandorafms.mssql_monitor.disco` from this repository or its GitHub Releases.
2. In Pandora FMS Console, open **Management → Discovery → Applications / Manage DISCO packages** (exact menu label may differ by build).
3. Select **Load/Upload DISCO** and upload the `.disco` file. Do **not** extract the archive before uploading.
4. Create a Discovery **Application** task for this extension, select the Discovery server and an execution interval (start with **300 seconds**).
5. Fill in the target host, port, database/service name, monitoring username/password and Pandora agent/group.
6. Enable the desired built-in groups and optionally create custom SQL modules; save the task.
7. Run the task, then check **Discovery Task execution summary**, resulting Pandora agent/modules and collection log.

The `.disco` file is a ZIP-format archive with a `.disco` extension. `discovery_definition.ini` must be located at the **archive root**.

## Configuration

| Setting | Purpose |
|---|---|
| Target host / port | Database endpoint reachable from Pandora Discovery server |
| Database / service | Database to connect to (Oracle uses a **service name**) |
| Monitoring credentials | Dedicated low-privilege database account |
| Agent name and group | Agent grouping in Pandora FMS |
| Built-in groups | Select which predefined metrics to collect |
| Custom SQL modules | Add up to ten custom monitoring modules |
| Result mode | `Auto`, `Table`, or `Scalar` for custom query output |
| Timeouts and overlap protection | Limit query runtime and duplicate task runs |

**SQL Server defaults:** database `master`, TCP `1433`, ODBC Driver 18, TLS encryption enabled, certificate trust disabled. Adjust these for your server.

## Built-in monitoring

The bundled SQL catalog contains **18 modules**. Available monitoring groups: **Basic Info; Databases; Connections; Performance; Security**. Examples include:

- SQL Server version/edition, database inventory and sizes, connections, requests, blocking, locks and buffer cache hit ratio.
- `Sessions:List` and `Database:List` are examples of string/table modules.

Some built-in metrics require additional privileges or may differ by database edition/version. An individual query error is logged; it does not necessarily indicate a failed network connection.

## Adding custom SQL modules

In the Discovery task wizard, open **Custom SQL modules**, enable the feature, and enter a module in the field-based form. Enable the next module slot when needed.

| Field | Example |
|---|---|
| Name | `Active Connections` |
| Datatype | `generic_data` for numeric or `generic_data_string` / `async_string` for text |
| Result mode | `Auto` (single-cell scalar; multiple rows/columns become table), `Table`, or `Scalar` |
| Unit | `connections`, `bytes`, `%`, `ms`, etc. |
| Module group | `Custom SQL` |
| SQL query | Read-only `SELECT` or `WITH` query |

### Numeric module example

```sql
SELECT COUNT(*) FROM sys.databases;
```

### String module example

```sql
SELECT @@VERSION;
```

### Tabular / snapshot module example

```sql
SELECT TOP (20)
    session_id, login_name, status, host_name, program_name
FROM sys.dm_exec_sessions
WHERE is_user_process = 1
ORDER BY session_id DESC;
```

For a multi-row result select a **string datatype** and **Table** mode. Custom SQL text can span multiple lines; each SQL textarea is materialized into its own Pandora temporary file to avoid truncation of multiline queries. Table output is intentionally bounded by a configurable maximum row count and may be truncated for large results.

**Query safety:** This extension applies a conservative read-only SQL syntax filter; this is **not a security boundary**. Always use read-only database permissions and avoid expensive full-table scans in frequent polling.

## Database permissions and security

Use a dedicated SQL login with CONNECT and the minimum SELECT/view permissions required. Some DMVs require `VIEW SERVER STATE` (older SQL Server) or `VIEW SERVER PERFORMANCE STATE` (SQL Server 2022+); do not grant `sysadmin` solely for monitoring. Confirm applicable permissions per target SQL Server version.

- Restrict access to database port(s) from the Pandora Discovery server only.
- Prefer encrypted and certificate-verified transport when supported; do not store credentials in Git, public logs or screenshots.
- Pandora writes sensitive temporary configuration files during execution. Protect the Pandora host, task permissions and temporary-file directories.
- Monitoring metrics that include session SQL text may expose application literals; review access to Pandora modules and logs.

## Database session usage

The Python collector opens **one `pyodbc.connect()` connection** per task execution and runs all built-in/custom queries sequentially through that connection; the session is closed after collection. Session-level statement timeout and lock timeout are configured.

The non-blocking lock prevents **overlapping runs of the same task on one Discovery host**. It is **not a distributed lock**: multiple tasks, different Pandora servers, or external monitoring clients can still create additional database sessions. Tune interval and timeouts according to query cost.

### Inspect collector sessions on the database

```sql
SELECT session_id, login_name, program_name, status
FROM sys.dm_exec_sessions
WHERE program_name = 'PandoraFMS-MSSQL-Discovery';
```

## Troubleshooting

- **Dependency error:** run the driver verification command above using `/usr/bin/python3` on the selected Discovery server.
- **Connection timeout/refused:** check DNS/IP, TCP port, listener/bind address, firewall, DB authentication, and TLS configuration.
- **Permission denied / missing view:** inspect the failing SQL module and grant only the minimum needed database permissions.
- **`N/A` on a table module:** select `Table` with a text datatype and test with a **new module name**, since Pandora may preserve the existing module type. Also inspect task execution and SQL errors.
- **Query result empty:** confirm the query produces rows under the same DB user and database context.
- **Task unexpectedly skipped:** check whether another run holds the local task lock.

**Default run log:** ``/var/log/pandora-scan/mssql_discovery.run.log``.

```bash
tail -100 /var/log/pandora-scan/mssql_discovery.run.log
```

## Source files and packaging

The published `.disco` archive contains:

```text
pandorafms.mssql_monitor.disco
├── discovery_definition.ini
├── pandorafms_mssql.py
├── disco_core.py
├── db_adapter.py
├── queries_builtin.json
└── README.txt
```

To inspect/rebuild from extracted source files (requires `zip` / `unzip`):

```bash
unzip -l pandorafms.mssql_monitor.disco
unzip -t pandorafms.mssql_monitor.disco
# From the directory containing the files above:
zip -j pandorafms.mssql_monitor.disco discovery_definition.ini pandorafms_mssql.py disco_core.py db_adapter.py queries_builtin.json README.txt
```

Do not zip a containing parent directory; the `discovery_definition.ini` file must be directly inside the archive. You can use 7-Zip with **ZIP** output and rename `.zip` to `.disco` as well.

## Compatibility and project status

- **Plugin version:** `1.0.1`.
- Tested at package/parser/syntax level during development; **end-to-end compatibility with every Pandora FMS build or DB engine version is not guaranteed**.
- Monitoring uses database views/statistics and therefore may differ across versions or privilege sets.
- SQL Server ODBC 18 normally validates TLS certificates when encryption is enabled. If certificate validation fails, configure a trusted CA/certificate rather than switching on `TrustServerCertificate` in production.

## Screenshoot
## Discovery
<img width="1659" height="890" alt="image" src="https://github.com/user-attachments/assets/29400069-c0e0-45c5-bcf5-27faa154f005" />
<img width="1664" height="836" alt="image" src="https://github.com/user-attachments/assets/b5173d9a-23ed-44fb-b135-1895535049b1" />
<img width="1664" height="828" alt="image" src="https://github.com/user-attachments/assets/04e318ad-a6f2-4173-9b0b-35db45f60db5" />
<img width="1664" height="875" alt="image" src="https://github.com/user-attachments/assets/991c966c-1352-4131-a493-4375549dc37b" />
<img width="1667" height="877" alt="image" src="https://github.com/user-attachments/assets/64ea6927-bd17-4b27-842c-3d4b54dd127c" />

## Contributing

Contributions are welcome for additional built-in metrics, query optimization, version compatibility, tests, documentation and safe monitoring use cases. Please include database version, Pandora FMS version, reproduction steps and sanitized logs when filing an issue. Do not submit passwords, private IP inventories or database query results containing sensitive values.

## License and trademarks

**License:** No license is included automatically in this README. The repository owner should add an explicit `LICENSE` file before distributing this project as open-source software. The name Pandora FMS and database/vendor names are trademarks of their respective owners. This is an **unofficial, independently developed** integration, not an official Pandora FMS package. Note that Pandora FMS documentation reserves the `pandorafms.` package `short_name` prefix for official integrations; consider a unique community/vendor prefix before public distribution.

## References

- [Pandora FMS: Discovery plugin/package workflow](https://pandorafms.com/manual/!current/en/documentation/pandorafms/monitoring/17_discovery_2)

- [Pandora FMS: .disco development and discovery_definition.ini](https://pandorafms.com/manual/!current/en/documentation/pandorafms/technical_reference/12_disco_development)

- [Pandora FMS: Data XML interface](https://pandorafms.com/manual/!current/en/documentation/pandorafms/technical_reference/01_development_and_extension)

- [Install Microsoft ODBC Driver for SQL Server on Linux](https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server)

- [pyodbc project documentation](https://github.com/mkleehammer/pyodbc)

- [SQL Server dynamic management views](https://learn.microsoft.com/en-us/sql/relational-databases/system-dynamic-management-views/system-dynamic-management-views)
