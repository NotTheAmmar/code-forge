# CodeForge Backup & Disaster Recovery Runbook

**Version:** 1.0 (Production & Final Jury Deployment)  
**Scope:** PostgreSQL relational data (`pg_data`), Redis cache/pubsub persistence (`redis_data`), and file assets (`submissions`).

---

## 1. Volume Architecture Overview

CodeForge leverages Docker named volumes for zero data loss across container lifecycle upgrades, rebuilds, and restarts:

| Volume Name | Service | Content | Criticality |
|---|---|---|---|
| `pg_data` | `db` (Postgres 16) | Users, Courses, Problems, Labs, Submissions, Badges, Modules, Exams, Violations | **Critical** |
| `submissions` | `api`, `worker` | Ephemeral temporary scratch source files & logs | Low |
| `redis_data` | `redis` | In-flight WebSocket sessions, rate limiting counters, broker queues | Medium |
| `grafana_data` | `grafana` | Custom instructor analytics dashboards & dashboard state | Low |

---

## 2. PostgreSQL Live Database Backup (Zero Downtime)

PostgreSQL supports non-blocking live logical backups using `pg_dump`. It does not require pausing the application or locking tables.

### 2.1 Single-Command Immediate Backup

Run directly on the host machine:

```bash
# 1. Create a timestamped backup directory
mkdir -p ./backups

# 2. Run pg_dump in compressed custom format (-Fc)
docker compose exec -T db pg_dump -U codeforge -d codeforge -Fc > "./backups/codeforge_backup_$(date +%Y%m%d_%H%M%S).dump"

# 3. Verify backup file integrity
ls -lh ./backups/
```

### 2.2 Plaintext SQL Dump (Human-Readable)

For SQL inspection or cross-version migrations:

```bash
docker compose exec -T db pg_dump -U codeforge -d codeforge --clean --if-exists > "./backups/codeforge_backup_$(date +%Y%m%d).sql"
```

---

## 3. Automated Backup Cron Configuration

To automate daily backups at 02:00 AM with 14-day rolling retention:

### 3.1 Backup Script (`/usr/local/bin/codeforge-backup.sh`)

```bash
#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="/var/backups/codeforge"
CODEFORGE_DIR="/home/ammar/Programs/code-forge"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "${BACKUP_DIR}"

cd "${CODEFORGE_DIR}"
docker compose exec -T db pg_dump -U codeforge -d codeforge -Fc > "${BACKUP_DIR}/codeforge_${DATE}.dump"

# Prune backups older than 14 days
find "${BACKUP_DIR}" -type f -name "codeforge_*.dump" -mtime +14 -delete
```

### 3.2 Crontab Entry

```cron
0 2 * * * /usr/local/bin/codeforge-backup.sh > /var/log/codeforge-backup.log 2>&1
```

---

## 4. Disaster Recovery & Database Restoration

### 4.1 Restoring onto an Active Instance

```bash
# 1. Transfer or locate the backup file
BACKUP_FILE="./backups/codeforge_backup_20261122.dump"

# 2. Terminate active backend connections to ensure clean restore
docker compose stop api worker

# 3. Restore database schema and records (using pg_restore)
docker compose exec -T db pg_restore -U codeforge -d codeforge --clean --if-exists < "${BACKUP_FILE}"

# 4. Restart backend services
docker compose start api worker
```

### 4.2 Restoring onto a Fresh Server

```bash
# 1. Clone repository on new machine
git clone https://github.com/NotTheAmmar/code-forge.git
cd code-forge

# 2. Run the turnkey setup
./codeforge-setup.sh

# 3. Stop backend workers before importing dump
docker compose stop api worker

# 4. Restore the database dump
docker compose exec -T db pg_restore -U codeforge -d codeforge --clean --if-exists < "/path/to/backup.dump"

# 5. Restart services
docker compose restart
```

---

## 5. Cold Storage / Docker Volume Snapshot

To create a full physical snapshot of the raw PostgreSQL Docker volume:

```bash
# Stop the database temporarily to flush WAL buffers
docker compose stop db

# Create an archive of the raw volume
docker run --rm \
  -v code-forge_pg_data:/data:ro \
  -v $(pwd)/backups:/backup \
  alpine tar -czvf /backup/pg_data_raw_$(date +%Y%m%d).tar.gz -C /data .

# Restart the database
docker compose start db
```

---

## 6. Verification & Health Monitoring

To verify database readiness and integrity after restoration:

```bash
# 1. Check PostgreSQL readiness
docker compose exec db pg_isready -U codeforge -d codeforge

# 2. Call the API readiness probe
curl -f http://localhost:8000/health/ready
# Expected: {"status":"ready","service":"codeforge-api","database":"connected","redis":"connected"}
```
