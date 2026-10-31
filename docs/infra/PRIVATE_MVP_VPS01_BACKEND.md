# Private MVP VPS.01: backend bundle and future installation

This is a preparation record, not authorization to modify the VPS or expose it.
The previous host inventory is historical; recheck it before any installation.
Keep public registration CLOSED, the existing C21/C22/C23 gates, and the
staging service disabled until a separate private-access decision. Do not put
real secrets, user data, SQLite databases, or encryption keys in the bundle.

## Rebuild and verify

Target: Ubuntu 24.04 **amd64**, existing CPython 3.13.17 prefix at
`/opt/worta/cpython/3.13.17`, PostgreSQL 16. The backend snapshot in this
artifact is commit `d0ade7c800053754eb211abb9b8d3314c1ed0726`. The separate
builder and wheel lock are tracked; obtain the exact 39 locked wheels from a
trusted wheelhouse. The builder refuses missing or mismatched hashes and uses
only tracked files from the requested revision:

```sh
python3 scripts/maintenance/build_vps_backend.py \
  --revision d0ade7c800053754eb211abb9b8d3314c1ed0726 \
  --wheelhouse "$WHEELHOUSE" --output "$OUTPUT/backend-linux-amd64.tar.gz"
shasum -a 256 "$OUTPUT/backend-linux-amd64.tar.gz"
```

For the reviewed inputs the archive SHA-256 is
`1693902cdda46ca75e00e259aa41b1ad8f6077018cbddd6f50fd2af55af06dde`;
two independent builds matched. `MANIFEST.json` covers source.tar, lock and
every wheel. Inspect the archive and verify that hash before transfer; do not
use an archive from an untrusted source. The independent CPython archive from
the prior reviewed build has SHA-256
`85e3a3a1e4826289ecc36319255de9dacf152a67a862ebcf02976fe7ed9a3cc4`.
It is not included in the backend archive because the target previously had
that runtime installed. Verify its version and dependencies rather than
assuming the old inventory is still current. A bare Ubuntu 24.04 additionally
needed `libsqlite3-0 libgdbm6t64 libgdbm-compat4t64 libreadline8t64` for
the retained CPython standard-library extensions. Confirm package availability
and review changes before installing anything on the actual host.

## Future deployment sequence

The following is a procedure to review before a later authorized deployment;
it is not executed by this task. Use the existing staging unit
`deploy/vps/worta-staging.service.example` (one worker on loopback,
`MemoryHigh=320M`, `MemoryMax=384M`), root-only `/etc/worta/staging.env`, and
the isolated `worta_stage` database and data paths from MVP6.0.08–10. Never
print the env file, pass its real secrets on a command line, or put them in Git.
Use systemd to load the root-owned mode-0600 environment. PostgreSQL remains
loopback/peer-only, and the existing Caddy staging template remains inactive
until the separately approved TLS, firewall and tester-CIDR review.

1. Confirm `uname -m` is `x86_64`, Ubuntu is 24.04, PostgreSQL is 16, the
   Python version is 3.13.17, and unit, paths, DB identity, grants, Caddy,
   firewall, SSH and current service state match the reviewed plan. Check
   `df -h /` and `free -h`; retain at least 2 GiB disk headroom after backup,
   unpack and install, and sufficient available memory for the migration and
   one worker. Existing ~1 GiB RAM figures are historical and not load tests.
2. Stop the staging service. With `umask 077`, make a new root-owned 0700
   backup directory. Capture the actual DB with `pg_dump -Fc`, capture the
   matching blob directory while writes are stopped, record SHA-256 and verify
   `pg_restore -l` and archive readability. Preserve an independently stored
   verified copy. Do not proceed without a usable matched backup and an
   approved recovery destination. Never overwrite a prior backup.
3. Transfer the verified bundle through the approved SSH identity to a fresh
   root-owned 0700 directory, verify SHA-256 on the host, and unpack it there.
   Preserve the old app and venv as a rollback pair. Unpack `source.tar` into a
   new app directory and make a new venv using the existing Python; install
   offline from the bundle using `pip install --no-index --find-links wheels
   --require-hashes -r requirements-backend-linux-amd64-py313.lock`, then run
   `pip check`. Verify the fixed `WorkingDirectory` and `ExecStart` of the
   reviewed systemd unit resolve to the selected new app and venv before use.
4. Record `alembic current` and `alembic heads`. Using the separately reviewed
   migration identity with temporary schema CREATE rights, run `alembic upgrade
   head` with the private production environment, then verify exactly one head,
   `game_loss_v2`. Revoke migration privileges afterward. Reconcile runtime DML
   and sequence privileges for **new** tables against the existing grants;
   runtime must lack database/schema CREATE and policy UPDATE, and retain its
   two-connection limit. Confirm registration is still `closed` in PostgreSQL.
5. Start the existing service, without enabling public access. Check systemd
   status, loopback `/health` and `/ready`, registration status and an anonymous
   admin denial. Verify no public 8000/5432 listener, and review logs without
   exposing credentials. SMTP and public HTTPS require separate configuration
   and testing before any invitation is sent. Do not create real accounts here.
6. On failure stop the service and preserve its logs, the new app, DB and blobs.
   If the DB has not changed and compatibility is verified, select the saved
   old app/venv pair. If migration or writes occurred, do **not** blindly use
   an old binary or downgrade in place: restore the matched DB and blobs to a
   new isolated target, validate them, and switch only after a separate reviewed
   recovery decision. Never delete or overwrite the only copy.

For step 2, after verifying the exact database and blob paths, an example using
the historical staging names is below. Set `backup_dir` to a **new**, reviewed
absolute path and run under a privileged shell. The service must be stopped and
all writers quiescent before taking the paired copies:

```sh
systemctl stop worta-staging.service
systemctl is-active --quiet worta-staging.service && exit 1
umask 077
mkdir -- "$backup_dir"                  # fails if it already exists
chmod 700 "$backup_dir"
sudo -u postgres pg_dump -Fc -d worta_stage > "$backup_dir/database.dump"
tar -C /var/lib/worta/staging/blobs -cf "$backup_dir/blobs.tar" .
pg_restore -l "$backup_dir/database.dump" >/dev/null
tar -tf "$backup_dir/blobs.tar" >/dev/null
sha256sum "$backup_dir/database.dump" "$backup_dir/blobs.tar" > "$backup_dir/SHA256SUMS"
sha256sum -c "$backup_dir/SHA256SUMS"
```

If the current blob path differs, stop and substitute only after inspecting the
actual configuration without printing secrets. The commands prove archive
readability, not recovery; restore and validate a copy on the approved isolated
target. For step 3, from inside the unpacked bundle, the offline install commands
are `python3.13 -m venv /opt/worta/staging/venv-new` and
`/opt/worta/staging/venv-new/bin/pip install --no-index --find-links "$PWD/wheels" --require-hashes -r requirements-backend-linux-amd64-py313.lock`,
followed by `/opt/worta/staging/venv-new/bin/pip check`. Use the verified WORTA
Python's absolute path instead of relying on PATH. Before step 4, explicitly
review the migration role, peer connection and temporary grants against the
actual host; a generic command containing the runtime credentials would be
unsafe. The migration command itself is `venv-new/bin/alembic upgrade head`
from the new app directory with the approved migration environment.

For step 3, transfer to a newly created private directory using the approved SSH
alias, then compare the resulting digest with the value above before extraction:

```sh
# Local machine; VPS is the reviewed SSH alias and OUTPUT contains the bundle.
ssh "$VPS" 'umask 077; mkdir "$HOME/worta-vps01-transfer"'
scp "$OUTPUT/backend-linux-amd64.tar.gz" "$VPS:worta-vps01-transfer/"
ssh "$VPS" 'sha256sum "$HOME/worta-vps01-transfer/backend-linux-amd64.tar.gz"'
```

Stop if the digest differs. Prepare source and dependencies at new paths before
switching the unit's fixed paths, and retain the old app/venv pair.

## Local rehearsal and limits

An amd64 Ubuntu 24.04 container under emulation installed the exact bundle
offline. The retained CPython was verified against its recorded hash; the four
OS libraries above were installed in that disposable container. `pip check`,
production dependency resolution and imports passed. Empty PostgreSQL 16
migrated to `game_loss_v2`; a second database upgraded from the previously
deployed `private_invitations` head, and repeat upgrade passed. The production
FastAPI process served loopback `/health` and `/ready`, rejected public signup,
accepted synthetic login, rejected a bad password and unauthorized invitation,
and returned 503 for an administrator invitation with SMTP unset. An unprivileged
runtime role with a two-connection limit passed health, readiness and login.
An actual process stop/restart retained the test account. A mode-0600 custom
dump restored into a new database with that account and head; a separate random
blob archive restored byte-for-byte. No real SMTP, Caddy, systemd service,
network exposure, E2EE client-to-server flow, 1 GiB workload or physical x86
host was tested by this container drill. A random blob is not an E2EE proof.
Those checks and the owner-approved independent backup/restore plan remain open.
One idle emulated-container sample showed 169.7 MiB for the application
container and 99.0 MiB for PostgreSQL; this includes container overhead and is
not a measurement or capacity guarantee for the actual VPS.
