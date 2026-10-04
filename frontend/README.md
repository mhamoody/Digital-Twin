# Course Twin — React instructor workspace

The real frontend migration, on branch **reactvite**. This is not the earlier
in-memory mock under `artifacts/react-focus-demo`.

**Current gate: policies and model operations (Phase 3).** Login, reads and instructor
edits use FastAPI and its real authorization/database. Flags, watchlists,
priority, audited support actions, follow-ups, resources and academic/risk
charts, course-policy editing, analysis queue/automation controls and safe
diagnostics are implemented locally. Full parity/usability is the next gate.
Streamlit remains the hosted operational interface; React has not been
deployed to Lobot.

## Code map

- `src/App.tsx`: session, navigation, course/checkpoint/identity context, shell.
- `src/api/contracts.ts`: TypeScript types **and runtime JSON validation**.
- `src/api/client.ts`: same-origin authenticated requests, safe errors, timeout.
- `src/hooks/useResource.ts`: cancellable reads; no old-course/student flash.
- `src/hooks/useSave.ts`: CSRF, optimistic concurrency and explicit idempotent
  retries after an uncertain response; no automatic mutation retries.
- `src/hooks/editGuard.tsx`: pending-save and unsaved-draft navigation guard.
- `src/pages/InstructorActions.tsx`, `SupportRecord.tsx`: audited instructor
  markers and support history, with no automatic student messaging.
- `src/pages/AcademicRecords.tsx`, `RiskHistory.tsx`: publication-safe grades,
  practice/assessed distinction, required-due resource completion and versioned
  risk history. `supportComparison.ts` rejects incompatible before/after facts.
- `src/pages/CourseSettings.tsx`, `src/api/policyContracts.ts`: all course-policy
  fields, draft-only presets, validation, revision conflicts and audited saves.
- `src/pages/ModelHealth.tsx`, `AnalysisControls.tsx`: actual model/worker/course
  state, learner/week/all-week queues, explicit retries, auto-discovery and resume.
- `src/hooks/useAnalysisStatus.ts`: sequential, visible-page progress polling;
  failed reads hide previously displayed counts. No implicit mutation.
- `src/hooks/useOperation.ts`, `src/components/OperationDialog.tsx`: confirmation
  and single-flight requests for operations without an idempotency guarantee.
- `src/pages/AnalysisProvenance.tsx`, `DemoGuide.tsx`: safe validation traces,
  historical/baseline distinctions and verified synthetic scenario navigation.
- `src/pages/`: overview, roster and student evidence/history screens.
- `src/styles.css`: responsive design tokens and page/component styling.
- `vite.config.ts`: Vite build and optional development API proxy.
- `../src/digital_twin/api/browser_auth.py`: server-managed pilot sessions.
- `../docs/22_react_migration.md`: phases and feature-parity checklist.

## Build

Use Node 22.12+ (tested with Node 24) and the project's Python environment.

```powershell
cd E:\Z1\GP\Digital-Twin\frontend
npm.cmd ci
npm.cmd run build
```

The generated `dist/` bundle is served by FastAPI; Vite's development server is
not the production hosting solution. `node_modules/`, `dist/`, credentials and
all learner datasets stay untracked.

## Isolated local preview (this workspace)

The local validation helper lives in the existing ignored `tests/` directory.
It creates only a separate synthetic database and a test-only instructor. It
does not call Ollama, restore a live database, or change Lobot services.

```powershell
cd E:\Z1\GP\Digital-Twin
python tests/run_react_preview.py
```

Open **http://127.0.0.1:18001/**. Username: `preview`. Read the generated password
locally from `var/auth/react-preview-login.json`; do not paste it into chat or
Git. Restarting the helper generates a new preview password. Stop with Ctrl+C.
The preview uses generated records and **rules-baseline-v3**, not live Qwen.
Do not launch a second copy on the same port. The helper is local-only and is
not included in Git because the repository excludes `/tests/`.

For a fresh clone, an operator can run the existing account/data preparation
workflow against a separate pilot database, then use the environment below.
Do not use the real hosted database for development testing.

## Same-origin serving configuration

Set these in the API process environment; never in `VITE_*` variables:

```text
DIGITAL_TWIN_BROWSER_ENABLED=1
DIGITAL_TWIN_BROWSER_ORIGIN=http://127.0.0.1:18001
DIGITAL_TWIN_BROWSER_SECURE=0
DIGITAL_TWIN_BROWSER_PATH=/
DIGITAL_TWIN_AUTH_FILE=<absolute path to the dedicated account file>
DIGITAL_TWIN_DATABASE_URL=<dedicated pilot database URL>
DIGITAL_TWIN_FRONTEND_DIST=<absolute path to frontend/dist>
```

```text
python -m uvicorn digital_twin.api.app:app --host 127.0.0.1 --port 18001 --workers 1
```

Without `DIGITAL_TWIN_BROWSER_ENABLED=1`, existing Streamlit behavior stays in
place. Browser cookies default to `Secure`; disabling it is accepted only with
an explicit loopback HTTP origin. No wildcard CORS or browser signing key.

For Vite hot reload: run `npm.cmd run dev` and use
`DIGITAL_TWIN_BROWSER_ORIGIN=http://127.0.0.1:5175` in the API process. Vite proxies
`/api` to loopback port 18001, so the browser still sees one origin. Use the
FastAPI-served production build for acceptance checks.

## Hosting/security boundary

- One API worker for the current bounded in-memory session store. Restarts log
  users out. Replicated deployment requires a shared session/rate-limit store.
- Sessions use opaque HttpOnly/SameSite cookies, 30-minute inactivity expiry,
  eight-hour absolute expiry, request-origin and CSRF checks for mutations.
- Account removal, role/password changes and current grants are checked again
  for every authenticated request. No student records or tokens in localStorage.
- Login throttling is a pilot safeguard, not a substitute for institutional SSO
  or a production edge rate limiter. Behind a proxy, limits may be shared by
  users with the same visible client address.
- Browser data contracts reject malformed responses rather than inventing risk
  scores. Request failures do not trigger automatic mutation retries.
- Hash navigation and relative asset/API paths support a proxy directory. For
  Lobot later, use its exact HTTPS origin, `Secure=1`, and the assigned
  `/user/<group>/proxy/<port>/` cookie path. A local prefix simulation passed;
  real hosted authentication and deployment have **not** been verified yet.
- Pilot account login is not LTI or Brightspace/onQ SSO. These remain separate
  institution-approved integration tasks.

## Validation

```text
npm.cmd run build
npm.cmd audit --audit-level=high
python -m pytest tests/test_browser_auth.py tests/test_workspace_security.py tests/test_workspace_instructor_phase2.py tests/unit/test_dashboard_client.py tests/unit/test_dashboard_auth.py -q
python tests/check_react_foundation.py
python tests/check_react_instructor_actions.py
python tests/check_react_phase2_edges.py
python tests/check_react_phase3_browser.py
node tests/check_react_academic_semantics.mjs
node tests/check_react_policy_semantics.mjs
node tests/check_react_phase3_semantics.mjs
python -m pytest tests/test_workspace_policy_v3.py tests/test_analysis_automation.py tests/test_analysis_diagnostics.py tests/test_inference_reliability.py -q
```

Run Python commands from the repository root; browser checks need the isolated
preview running, Python Playwright and Edge. Evidence is in the ignored folder
`artifacts/react-migration/`. The current gate is not a full accessibility audit,
penetration test or end-to-end replacement acceptance. The instructor-action
check writes labeled test support records only to the isolated synthetic
preview. Never point these checks at the hosted database.

Support history always represents current instructor records even when viewing
earlier evidence. Planned actions require explicit completion/cancellation;
case closure does not silently finish plans. Follow-up scheduling/clearing is
explicit. If a save response is lost, the editor freezes that request and lets
the instructor retry its exact idempotency key or inspect history first.

Policy, automation and course-resume operations do **not** use that retry
contract. A lost response freezes the request and asks for a saved-state read
before another decision. Policy edits retain historical assessments; saved
results do not become current until reassessed under the new policy.

Progress polls every ten seconds after the previous read finishes, while the
page is visible. Queueing is not completed inference; refreshing is not an LMS
import. Model availability does not prove successful inference. Course resume
does not start a worker or clear a shared-service pause. Pre-inference quality
abstention, validated model output and predictive accuracy remain distinct.

Phase 3 browser checks change settings/automation and queue synthetic records
only in the isolated preview. No worker is started; pause/failure displays use
controlled HTTP fixtures. Live Qwen inference and hosted deployment verification
remain a later gate, not something these local checks establish.

Implementation references: [Vite backend integration](https://vite.dev/guide/backend-integration),
[FastAPI static files](https://fastapi.tiangolo.com/tutorial/static-files/), and
[OWASP CSRF prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).
