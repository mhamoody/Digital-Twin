# Parallel React candidate on Lobot

React runs on **8502**; Streamlit remains on **8501**, the original API on
**8000**, and the existing analysis worker is unchanged. Both interfaces use
the same database, instructor grants and approved model configuration. A save
or queue request in React is real, not a mock. Do not launch another worker.

The new service is a single FastAPI process serving the built frontend and
authenticated API together. Its source lives in a separate Git worktree, so
the working tree used by the running worker is not switched or overwritten.
There are no database migrations in this rollout.

## First setup

In the Lobot terminal, with the original project already configured:

```bash
cd ~/Digital-Twin
git remote set-branches --add origin reactvite
git fetch origin reactvite
git worktree add --track -b reactvite ../Digital-Twin-react origin/reactvite
cd ~/Digital-Twin-react
```

Run the worktree command only once; if that path or branch already exists,
inspect it rather than deleting or recreating it.
The additional fetch branch is needed for the original single-branch clone;
it does not switch the operational checkout away from `agent/align-strong-llm`.

### Build choices

If Node **22.12 or newer** is available in the Lobot terminal:

```bash
bash deploy/lobot/react.sh build
```

The initial Lobot environment has Node 18, so the alternative is a locally
built release. Build the committed frontend on the development computer:

```powershell
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run build
python scripts/frontend_release.py pack
```

Transfer the produced ZIP to `~/Digital-Twin/artifacts/react-release/` via
JupyterLab. Use the **exact** SHA-256 printed by the packaging command:

```bash
cd ~/Digital-Twin-react
../Digital-Twin/.venv/bin/python scripts/frontend_release.py install \
  --archive ../Digital-Twin/artifacts/react-release/COMMIT.zip \
  --sha256 EXACT_SHA256
```

The installer verifies archive and asset hashes, source commit, path boundaries
and size limits. It refuses a non-empty target instead of overwriting an older
build. Never disable these checks to make a mismatched release install.

## Start, check and stop only React

```bash
cd ~/Digital-Twin-react
bash deploy/lobot/react.sh start
bash deploy/lobot/react.sh status
```

Open **https://lobot.cs.queensu.ca/user/group-digi2026-g12/proxy/8502/** and use
your existing instructor account. JupyterHub and instructor sign-in remain
separate gates. Cookies are Secure/HttpOnly, scoped to this proxy directory.
The in-memory session store uses one API process; restarting React logs its
browser users out, not Streamlit users.

```bash
tail -n 60 ~/Digital-Twin/var/log/react-api.log
bash deploy/lobot/react.sh stop
```

`stop` checks Linux process start time and command identity, then uses pidfd
signalling to avoid acting on a reused PID. It never stops port 8000, port 8501,
Ollama or the worker. A failed start cleans up only the new React process.
Keep logs private: they can contain authorized course/learner identifiers.
The launcher waits for the child command to finish its initial exec transition
before recording its identity. On Lobot's Conda Python, which omits Python pidfd
wrappers, it calls glibc's pidfd functions instead; it never falls back to an
unverified process-number kill.

## Update and rollback

Do not run the original `stop.sh` or switch its branch to update React. First
ensure no instructor is submitting a save in React, then stop only React.
Record `git rev-parse HEAD` and preserve its existing `frontend/dist` in a
timestamped backup before updating the React worktree with `git pull --ff-only`.
Build or install the matching new release, start React and verify sign-in.
Keep the old worktree commit and bundle for rollback; do not reset/delete user
files. Streamlit on 8501 remains the immediate operational fallback.

## Acceptance and limits

- Verify correct asset release, protected sign-in, allowed courses, names/ID
  mode, learner evidence, settings and model/worker progress through the proxy.
- Current course-operation workflows are migrated. The verified October 8 release
  includes separate **v1** learner activity, paginated historical alerts, case
  creation/reuse, versioned actions, follow-ups and alert reviews under
  **Earlier support history**. Original v1 records remain distinct from v2
  cases. Streamlit is still a fallback, not deleted or stopped by this rollout.
- Readiness and saved analyses are not proof of a new inference. Report any
  real model check separately, with its sample scope and validation result.
- Institutional LTI/onQ SSO, production availability and a full accessibility
  certification are not supplied by this parallel pilot deployment.

The October 8 application release is `30db835`; its actual hosted acceptance and
backup checks are recorded in `docs/22_react_migration.md`. Documentation-only
follow-up commits do not imply a rebuilt or restarted application.
