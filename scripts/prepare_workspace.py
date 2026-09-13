"""Safely add a rich synthetic workspace and preserve existing empirical tables."""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
from pathlib import Path

from sqlalchemy.engine import make_url

from digital_twin.dashboard.auth import load_accounts, normalize_username
from digital_twin.persistence import create_twin_engine, create_validation_schema
from digital_twin.workspace.legacy import import_legacy
from digital_twin.workspace.store import Store
from digital_twin.workspace.synthetic import generate_dataset, seed_support_history


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=os.environ.get("DIGITAL_TWIN_DATABASE_URL"))
    parser.add_argument("--learners-per-course", type=int, default=120)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument(
        "--grant-demo-access",
        help="Existing account to grant only these fictional demonstration courses",
    )
    parser.add_argument(
        "--baseline",
        action="store_true",
        help="Compute explicitly labeled comparison rules; never impersonate Qwen",
    )
    args = parser.parse_args()
    if not args.database_url:
        parser.error("Set DIGITAL_TWIN_DATABASE_URL or --database-url")
    os.umask(0o077)
    parsed_url = make_url(args.database_url)
    if parsed_url.drivername.startswith("sqlite") and parsed_url.database not in {None, ":memory:"}:
        Path(parsed_url.database).parent.mkdir(parents=True, exist_ok=True)
    key_file = Path(os.environ.get("DIGITAL_TWIN_API_KEY_FILE", "var/auth/api.key"))
    key_file.parent.mkdir(parents=True, exist_ok=True)
    if not key_file.exists():
        with key_file.open("xb") as handle:
            handle.write(secrets.token_hex(32).encode())
        key_file.chmod(0o600)
    engine = create_twin_engine(args.database_url)
    if engine.dialect.name == "sqlite":
        create_validation_schema(engine)
    print("Legacy mapping (original tables untouched):", import_legacy(engine))
    dataset = generate_dataset(
        seed=args.seed, learners_per_course=args.learners_per_course, weeks=16
    )
    store = Store(engine)
    print("Synthetic import:", store.ingest_dataset(dataset))
    print("Synthetic support history:", seed_support_history(store, dataset))
    output = Path("artifacts/workspace")
    output.mkdir(parents=True, exist_ok=True)
    (output / "scenario_oracle.json").write_text(
        json.dumps(dataset.get("oracle", []), indent=2), encoding="utf-8"
    )
    if args.grant_demo_access:
        username = normalize_username(args.grant_demo_access)
        account_file = Path(os.environ.get("DIGITAL_TWIN_AUTH_FILE", "var/auth/instructors.json"))
        accounts = load_accounts(account_file)
        if username not in accounts:
            parser.error("The named instructor account does not exist; no account was created.")
        document = json.loads(account_file.read_text(encoding="utf-8"))
        courses = [c["presentation_id"] for c in dataset["courses"]]
        entry = document["accounts"][username]
        entry["allowed_presentations"] = list(
            dict.fromkeys(entry["allowed_presentations"] + courses)
        )
        backup = account_file.with_suffix(".pre-workspace.json")
        if not backup.exists():
            shutil.copy2(account_file, backup)
            backup.chmod(0o600)
        temp = account_file.with_suffix(".workspace.tmp")
        temp.write_text(json.dumps(document, indent=2), encoding="utf-8")
        temp.chmod(0o600)
        temp.replace(account_file)
        print("Fictional course access added to:", username)
    if args.baseline:
        from digital_twin.workspace.bootstrap import prepare_baselines

        for course in store.courses():
            for week in course["checkpoints"]:
                store.enqueue(course["presentation_id"], week, model_kind="baseline")
        prepare_baselines(store, progress=lambda message: print(message, flush=True))
        print("Job status:", store.job_summary())
    engine.dispose()
    print(
        "Workspace ready. Synthetic risk scores are demonstrations, "
        "not measured real-world probabilities."
    )


if __name__ == "__main__":
    main()
