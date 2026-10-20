"""Run one protected application's durable inference worker (no HTTP listener)."""

from __future__ import annotations

import argparse
import logging
import os

from digital_twin.persistence import create_twin_engine
from digital_twin.workspace.store import Store
from digital_twin.workspace.worker import run_worker


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Process at most one persisted job")
    parser.add_argument("--poll-seconds", type=float, default=2)
    parser.add_argument("--model-kind", choices=["llm", "baseline"], default=None)
    args = parser.parse_args()
    url = os.environ.get("DIGITAL_TWIN_DATABASE_URL")
    if not url:
        parser.error("DIGITAL_TWIN_DATABASE_URL must be configured by the deployment environment.")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    engine = create_twin_engine(url)
    try:
        run_worker(
            Store(engine),
            once=args.once,
            poll_seconds=args.poll_seconds,
            model_kind=args.model_kind,
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
