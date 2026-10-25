# MVP6.0.08 — isolated VPS staging provisioning

## Before the VPS changes (2026-10-25)

Target: SpaceWeb `195.208.60.94`, SSH as `worta-admin` with strict host-key
checking. Local `6.0` and `origin/6.0` both pointed to
`b7b1906a46e642a796ed4eae992d4287d084074a`; the checkout was clean.
This section was recorded before changing the VPS so the new resources can be
identified and removed without touching the existing installation.

- Ubuntu 24.04, kernel `6.8.0-147-generic`; `postgresql@16-main`, Caddy and
  SSH active. The PostgreSQL umbrella unit reported `inactive`, while the
  actual `16-main` cluster was `online` and `active`.
- PostgreSQL had only the `postgres` database and login role. It listened on
  `127.0.0.1:5432`; local connections used `peer`, and all TCP HBA entries
  rejected connections. `max_connections=20`, with 3 superuser-reserved.
- Caddy listened only on `127.0.0.1:8080` and returned 404 for
  `app.worta.ru`, `api.worta.ru`, and `test.worta.ru`.
- UFW was active, with inbound TCP/22 allowed for IPv4 and IPv6 only. No
  service listened on public 80, 443, 5432, or 8080.
- Available RAM: 676,257,792 bytes (~645 MiB); no swap. Free root disk:
  6,955,573,248 bytes (~6.48 GiB). The root filesystem had 530,097 free
  inodes.
- The `worta_stage` OS user/group and PostgreSQL role/database did not exist.
  `/opt/worta/staging`, `/etc/worta`, `/var/lib/worta`,
  `/var/cache/worta`, and `/etc/systemd/system/worta-staging.service` did not
  exist. Existing `/opt/worta/cpython/3.13.17` was retained.
- SHA-256 of unchanged baseline configs: `pg_hba.conf`
  `b67a064b18dd0af7ce20f97c2c044110b2a40e746d723ccecb6dfee659970039`,
  `postgresql.conf`
  `a8917323495057fe87f0a222ee997da43a0b468f1ffbf9ca754716d6ca027bc7`,
  live Caddyfile
  `97e39ff74abf7d6bc15c3ff7630c26d55e5a188c7395001ef0230989208408c9`,
  `sshd_config`
  `7962003fec1be865b919f3e48185b0a80905774e888e081f530ce1ffa9a22f16`.

## Planned isolated resources and rollback boundary

The stage creates only `worta_stage` OS user/group, PostgreSQL login role and
empty database of the same name, `/opt/worta/staging`, `/etc/worta`, and
`/var/lib/worta/staging`. The PostgreSQL role uses Unix-socket peer auth as
the matching OS user, so no HBA change or database password is required. The
database remains owned by `postgres`; the staging role receives only CONNECT
and schema USAGE before any migration. Its connection limit is 2. An
application auth secret is generated on the VPS and stored only in a root-owned
mode-0600 environment file. The systemd unit stays outside the unit search
path and is neither enabled nor started.

Rollback is authorized only while the database remains empty and no stage
data exists. First inspect exact paths and database contents; stop if any new
data, connections, or an installed/active unit appears. Remove the inactive
unit template and staging directories created by this stage, including the
environment file, after verifying their exact identities. Drop only database
`worta_stage`, then only role `worta_stage`, then delete only the matching OS
account/group. Do not touch `/opt/worta/cpython`, the `postgres` database or
role, SSH/UFW/Caddy configuration, other databases, or provider snapshots.
If any staging data exists, capture a matched database/blob backup and obtain
a new restoration decision before deleting anything. No automatic rollback
script is installed.

## Execution record

**Prepared, inactive; not a backend deployment.** The stage added the
`worta_stage` system account (locked login shell `/usr/sbin/nologin`) and group.
`/opt/worta/staging/app` is an empty root-owned application destination;
`/opt/worta/staging/venv` is an empty Python 3.13.17 virtual environment made
with `--without-pip` (no backend or dependencies installed). Both are under a
`root:worta_stage` mode-0750 parent. `/opt/worta/staging/config` is
`root:root` mode 0700. `/var/lib/worta/staging/{data,blobs,tmp}` are empty,
owned by `worta_stage:worta_stage` and mode 0700. `/etc/worta` is root-only
mode 0700. No user profile was copied or accessed.

`/etc/worta/staging.env` is `root:root` mode 0600. The application auth
secret was generated on the VPS with `secrets.token_urlsafe(48)`; no value was
printed or stored in Git. The file has production/web flags, an exact Unix
socket database URL, the isolated data/blob paths and future
`https://test.worta.ru` origin. It has no SMTP settings or database password.
Only metadata and a boolean check of secret length were inspected. The
`worta_stage` account cannot read the environment file directly; systemd's
manager would load it if a later, separately approved install activates the
unit.

PostgreSQL now has an **empty** `worta_stage` database, owned by `postgres`,
and a `worta_stage` LOGIN role. The role has no password, superuser,
CREATEDB, CREATEROLE, replication, bypass-RLS or role inheritance privilege.
It has a 2-connection limit, CONNECT on its database and USAGE on `public`;
it has no database CREATE/TEMP or schema CREATE rights. PUBLIC access to the
staging database and schema was revoked. No tables, migrations or accounts
were created. The role successfully queried its database through peer-auth
Unix socket; TCP to `127.0.0.1:5432` was rejected. The dedicated future
migration role and runtime table grants must be designed at the later
backend/migration stage; the current application role cannot run Alembic.

The prepared unit is at
`/opt/worta/staging/config/worta-staging.service`, SHA-256
`4c6874361b9e41c19097f8bf1f2b9e890fb74d38a9a19dd10a6b4efab653c0c3`,
identical to `deploy/vps/worta-staging.service.example`. It passed
`systemd-analyze verify`; there is no corresponding file in
`/etc/systemd/system`, so it is neither registered, enabled nor started. It
specifies one Uvicorn process on `127.0.0.1:8000`, the production environment,
isolated write path, no access log, `MemoryHigh=320M`, `MemoryMax=384M`,
`TasksMax=32`, and bounded restart (`StartLimitBurst=3` per 300 seconds).
`CloudDatabase` in the accepted code has pool size 2 and zero overflow. The
unit limits are preparatory; they have not been load-tested on this VPS.

Post-change checks: PostgreSQL `postgresql@16-main`, Caddy and SSH active;
Caddy returned 404 for all three closed hosts. `ss` showed only SSH on
public IPv4/IPv6, PostgreSQL on `127.0.0.1:5432`, and Caddy on
`127.0.0.1:8080`. UFW still allows only TCP/22 inbound. The four baseline
config SHA-256 hashes above were unchanged. Available RAM at the final idle
sample was 679,927,808 bytes (~648 MiB), with no swap; free root disk was
6,953,148,416 bytes (~6.48 GiB). These idle samples do not prove loaded
backend/Argon2 capacity. The staging database reported 7,683,095 logical
bytes; no user tables were present.

### Exact rollback for this empty stage

First verify the unit is still absent from systemd, the database has no user
tables/connections, and the listed data/blob/tmp/app directories contain only
the files created here. If any condition fails, stop and obtain a new recovery
plan. With those checks satisfied, run as `worta-admin` with sudo:

```sh
sudo -u postgres dropdb worta_stage
sudo -u postgres psql -X -v ON_ERROR_STOP=1 -d postgres -c 'DROP ROLE worta_stage'
sudo rm -r /opt/worta/staging /etc/worta /var/lib/worta/staging
sudo rmdir /var/lib/worta
sudo userdel worta_stage
# Only if the private group still exists after userdel:
sudo groupdel worta_stage
```

`dropdb` deliberately has no force flag: active use blocks rollback. Removing
`/etc/worta` destroys the newly generated auth secret, so this rollback is
appropriate only before any accounts, migrations or tester data exist. No
original PostgreSQL, Caddy, SSH, UFW, DNS or provider backup setting changed;
those components need no rollback. The reported SpaceWeb snapshot service is
not a tested DB/blob restore mechanism.

**Gate:** MVP6.0.07 independent Cloud CI acceptance is pending per owner.
No backend bundle, package set, migration, administrator, invitation, Note
writer, ACK path or HTTPS endpoint was installed or activated. C21/C22/C23
and explicit owner approval remain prerequisites to starting the backend or
admitting testers. Registration stays CLOSED. Official Web progress stays
89.36%.
