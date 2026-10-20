"""Create or update the ignored instructor account file for a hosted pilot."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from digital_twin.dashboard.auth import (  # noqa: E402
    ALLOWED_ROLES,
    AccountConfigurationError,
    normalize_username,
    password_record,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("username")
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--role", choices=sorted(ALLOWED_ROLES), default="instructor")
    parser.add_argument(
        "--presentation",
        action="append",
        dest="presentations",
        required=True,
        help="Allowed course presentation ID; repeat for more than one course.",
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=Path(os.environ.get("DIGITAL_TWIN_AUTH_FILE", "var/auth/instructors.json")),
    )
    return parser.parse_args()


def main() -> None:
    os.umask(0o077)
    args = parse_args()
    try:
        username = normalize_username(args.username)
        if not args.display_name.strip():
            raise AccountConfigurationError("Display name cannot be empty.")
        presentations = [item.strip() for item in args.presentations if item.strip()]
        if not presentations:
            raise AccountConfigurationError("At least one course presentation is required.")
        password = getpass.getpass("Password (minimum 12 characters): ")
        confirmation = getpass.getpass("Confirm password: ")
        if password != confirmation:
            raise AccountConfigurationError("Passwords do not match.")
        password_data = password_record(password)
    except AccountConfigurationError as error:
        raise SystemExit(str(error)) from error

    payload = {"version": 1, "accounts": {}}
    if args.file.exists():
        try:
            payload = json.loads(args.file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise SystemExit("Existing account file cannot be read safely.") from error
        if payload.get("version") != 1 or not isinstance(payload.get("accounts"), dict):
            raise SystemExit("Existing account file is not a supported version 1 account file.")

    payload["accounts"][username] = {
        "display_name": args.display_name.strip(),
        "role": args.role,
        "allowed_presentations": list(dict.fromkeys(presentations)),
        "password": password_data,
    }
    args.file.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.file.with_suffix(args.file.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(args.file)
    try:
        os.chmod(args.file, 0o600)
    except OSError:
        pass
    print(f"Account {username!r} saved in {args.file}. The file must remain untracked.")


if __name__ == "__main__":
    main()
