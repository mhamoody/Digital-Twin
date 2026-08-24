# Remote hosting and LMS-neutral deployment

## Decision

The application will be deployable as a standalone, instructor-facing service
before it is connected to an LMS. The current remote pilot keeps three boundaries
separate:

1. **Data adapters** convert OULAD, controlled Moodle exports, or a future LMS API
   into the canonical observation and weekly-state contracts.
2. **Identity adapters** convert a pilot login, a future OIDC login, or an LTI 1.3
   launch into a pseudonymous reviewer, role, and allowed course context.
3. **The instructor application** uses stable FastAPI endpoints and PostgreSQL; it
   does not read Moodle, onQ, or LMS tables directly.

This means an onQ connection can be added later without rewriting the predictor,
database, alert lifecycle, evidence screens, or learner activity screens. Moodle
remains a local integration harness, not a dependency of the hosted application.

## What Lobot currently proves—and does not prove

Direct inspection and the 2026-08-24 capability probe show a
GitHub-OAuth-protected JupyterHub workspace with Python 3.12, a 49 GB mounted
Longhorn volume, `jupyter-server-proxy`, Git, and curl. Docker, Podman,
PostgreSQL tools, FastAPI, Streamlit, and psycopg were not preinstalled. FastAPI,
Streamlit, and psycopg can be installed in the project virtual environment; the
absence of a database server/container runtime means PostgreSQL cannot be hosted
inside this allocation as currently configured.

The JupyterHub allocation is sufficient for a small SQLite-backed interface and
login pilot while its pod is running. It does **not** prove an always-running
lifecycle, public port, stable domain, or institutional backup policy. Only the
Lobot administrators can confirm suspension/culling and service availability.

Run the non-secret capability probe from the Lobot terminal first:

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL> Digital-Twin
cd Digital-Twin
bash deploy/lobot/probe.sh
cat artifacts/lobot/probe.txt
```

The probe records commands, Python modules, storage information, listening port
numbers, and the JupyterHub routing prefix. It deliberately does not print
passwords, tokens, or environment-variable values.

## Path A: current Lobot/JupyterHub pilot

Use this path now for a small interface/login demonstration. The pilot uses a
file-backed SQLite database on the mounted project volume. This is acceptable
for one API process and low-concurrency demonstration access; it is not the
research or always-on deployment database. PostgreSQL remains required for the
group-VM deployment. FastAPI stays on loopback and only Streamlit is routed
through the authenticated Jupyter proxy.

### 1. Install the application

```bash
bash deploy/lobot/bootstrap.sh
cp deploy/lobot/env.example .env.lobot
chmod 600 .env.lobot
```

The supplied Lobot environment example selects
`var/data/digital_twin.sqlite3` and presentation `oulad:AAA:2013J`. The populated
`.env.lobot` file and SQLite database are ignored by Git.

### 2. Create instructor accounts

The remote pilot uses a versioned, ignored account file with scrypt password
hashes. Passwords are prompted and never stored in plaintext or placed on the
command line.

```bash
source .venv/bin/activate
python scripts/manage_instructor_accounts.py professor1 \
  --display-name "Professor One" \
  --role instructor \
  --presentation moodle-replay:AAA:2030A
```

Repeat the command for each instructor or supervisor. Repeating it for the same
username safely replaces that account and password. Each account sees only the
listed course presentation IDs. The API audit trail receives a hash-derived
reviewer ID, not the account username.

This account system is appropriate for a controlled project pilot behind
JupyterHub's outer GitHub login. It is not institutional single sign-on. There is
no password reset, MFA, central account deprovisioning, or LMS enrolment sync.

### 3. Transfer and restore the controlled pilot database

The OULAD directory and generated databases are deliberately ignored by Git, so
a fresh GitHub clone contains no student records. For this pilot, upload the
locally generated file below through the authenticated Lobot/Jupyter file
browser to a directory outside the repository, such as `~/incoming/`:

```text
data/processed/oulad_demo_phase3_v1/relational_validation.sqlite3
```

It contains the prepared `oulad:AAA:2013J` architecture demonstration. It is
about 94 MB and includes 383 learner enrolments, 1,464 weekly states and demo
predictions, and 142 alerts. The learner identifiers come from the public OULAD
release, but the file must still follow the project's approved educational-data
handling policy.

Restore it into the ignored pilot location before starting the service:

```bash
bash deploy/lobot/restore.sh ~/incoming/relational_validation.sqlite3
```

Do not email or commit the database. Even pseudonymized educational records
must follow the approved storage and transfer policy. `restore.sh` refuses to
proceed without an explicit confirmation and expects an empty database; it does
not clean or overwrite an existing database.

At startup, `initialize_pilot_database.py` adds any newer application tables to
the restored SQLite file without changing its existing learner, state,
prediction, or alert records. Do not present the risk values as model
performance: `simple-rules-v1` is still the architecture test double.

### 4. Start, open, and stop the service

```bash
bash deploy/lobot/start.sh
bash deploy/lobot/status.sh
```

`start.sh` prints a URL shaped like:

```text
/user/group-digi2026-g12/proxy/8501/
```

Open it through `https://lobot.cs.queensu.ca`. A remote professor must first be
authorized to enter the Lobot group workspace through GitHub, then use the
application account created above. An application password cannot bypass the
outer JupyterHub authorization.

```bash
bash deploy/lobot/backup.sh
bash deploy/lobot/stop.sh
```

Logs and PID files are under ignored `var/log/` and `var/run/`. Consistent SQLite
backups are under ignored `var/backups/`; copies must also be stored in an approved,
access-controlled backup location and a restore must be tested.

## Path B: recommended always-on group VM

For a dependable supervisor/instructor service, request a group-assignable VM,
DNS name, HTTPS routing, storage/backup policy, and firewall policy from the
School of Computing. Queen's CASLab documentation explicitly lists
group-assignable VMs as requestable project resources.

The prepared VM profile contains PostgreSQL 16, FastAPI, the protected Streamlit
dashboard, and Caddy HTTPS termination:

```bash
cd deploy/vm
cp env.example .env.vm
# Fill APP_DOMAIN and a long random database password.
mkdir -p ../../var/auth
# Create ../../var/auth/instructors.json using manage_instructor_accounts.py.
docker compose --env-file .env.vm -f compose.yml config
docker compose --env-file .env.vm -f compose.yml up --detach --build
docker compose --env-file .env.vm -f compose.yml ps
```

Populate the VM database through the same controlled process before instructor
use. To restore a custom-format dump into a newly initialized empty database,
stop `api` and `dashboard`, then pipe the dump to `pg_restore` inside `db`. Never
use a clean/overwrite restore without a separately verified backup and an
approved maintenance window.

Only ports 80 and 443 are published. PostgreSQL and FastAPI remain on the private
container network. Caddy obtains a certificate only when the supplied DNS name
resolves to the VM and inbound HTTPS is permitted. Run `backup.sh` from this
directory for a host-side PostgreSQL dump.

The Compose profile should be used on Lobot only if the capability probe and
administrators explicitly confirm Docker and persistent service hosting. A
Jupyter notebook allocation must not be treated as a production VM by
assumption.

## Practical instructor interface now

The standalone dashboard provides:

- password-protected, course-scoped instructor and supervisor accounts;
- course health, data origin, freshness, and quarantine status;
- a searchable full roster, including learners without alerts;
- weekly activity and assessment-event charts for each learner;
- latest checkpoint features with explicit missingness;
- a priority alert queue, evidence/provenance, uncertainty, score history, and
  audited human review;
- a visible warning that the current predictor is a temporary uncalibrated
  architecture test double.

The API is intentionally not published to the internet in either hosting
profile. The browser reaches the dashboard; the dashboard makes internal API
requests with the account's pseudonymous reviewer identity.

## Later integration with onQ or another LMS

No LMS integration is performed in this phase. The future adapter must provide
two different capabilities, which should not be confused:

1. **LTI 1.3 launch and identity:** course context, user identity/role, secure
   launch, and a link or embedded view from the LMS. This replaces the pilot
   login and maps the LMS course context to `presentation_id`.
2. **Learning-data access:** roster, grades, assessments, and activity/event
   records through institution-approved APIs, exports, or event services. LTI
   login alone does not automatically grant all historical learner activity.

For onQ, the team will eventually need Queen's approval and registration values
such as issuer, client ID, deployment ID, authentication URL, token URL, JWKS,
redirect/launch URL, and allowed course roles. Data access needs a separately
approved Brightspace API/service-account scope. For Canvas, Moodle, Open edX, or
another system, only the launch/identity and ingestion adapter change.

The future adapter acceptance gates are:

1. Validate signature, issuer, audience, nonce, state, deployment, course
   context, and instructor role on every launch.
2. Keep the LMS subject identifier out of application logs and derive a
   pseudonymous reviewer ID.
3. Maintain an explicit LMS-course-to-presentation mapping; never accept a
   browser-supplied arbitrary course ID.
4. Use read-only, least-privilege data scopes and an allowlist of required
   fields/endpoints.
5. Preserve source timestamps, missingness reasons, provenance, and ingestion
   freshness through the canonical contracts.
6. Reject students from instructor views, log human review mutations, and never
   contact students automatically.

## Go-live checklist

Before any real student data is hosted, obtain supervisor/institution approval
for the data location and retention policy; use HTTPS; restrict host and database
accounts; rotate every sample secret; schedule backups; test restore; define
monitoring and incident ownership; run accessibility and browser checks; and
perform a privacy/security review. The prepared scripts make the prototype
repeatable, but they do not by themselves authorize use of identifiable student
records.
