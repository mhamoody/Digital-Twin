"""Local operator diagnosis/resume; never modifies predictions or instructor accounts."""

import argparse
import json
import os
from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

from digital_twin.persistence import create_twin_engine
from digital_twin.workspace.llm import OllamaClient
from digital_twin.workspace.scheduling import runtime_spec
from digital_twin.workspace.store import Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["status", "resume-service", "resume-course"])
    parser.add_argument("--course")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    url = os.environ.get("DIGITAL_TWIN_DATABASE_URL")
    if not url:
        parser.error("Load .env.lobot first; database configuration is required.")
    try:
        parsed = make_url(url)
    except (ValueError, SQLAlchemyError):
        parser.error("Invalid database configuration; inspect it locally without sharing secrets.")
    if parsed.drivername.startswith("sqlite") and not Path(parsed.database or "").is_file():
        parser.error("Configured database does not exist; this command never initializes it.")
    if args.action != "status" and not args.confirm:
        parser.error("Resume requires --confirm after inspecting the pause reason.")
    if args.action == "resume-course" and not args.course:
        parser.error("--course is required for a course resume")
    pin = Path("var/models/predictor.json")
    if pin.is_file():
        try:
            value = json.loads(pin.read_text(encoding="utf-8"))["digest"]
            if not isinstance(value, str) or not value:
                raise ValueError("Invalid model digest")
        except (ValueError, KeyError, OSError):
            parser.error("The installed model identity file is invalid; inspect predictor.json.")
        # Match start.sh: use the operator's installed model identity for status and readiness.
        os.environ["DIGITAL_TWIN_LLM_DIGEST"] = value
    engine = create_twin_engine(url)
    try:
        store = Store(engine)
        if args.action == "resume-service":
            if OllamaClient().readiness()["status"] != "ready":
                parser.error(
                    "Model readiness failed; correct service configuration before resuming."
                )
            print(json.dumps(store.resume_service(), indent=2))
        elif args.action == "resume-course":
            print(json.dumps(store.resume_analysis(args.course), indent=2))
        else:
            spec = runtime_spec()
            courses = [c["presentation_id"] for c in store.courses()]
            if args.course:
                courses = [args.course]
            print(
                json.dumps(
                    {
                        "worker": store.get_runtime(),
                        "courses": {
                            course: {
                                key: value
                                for key, value in store.analysis_status(course, spec).items()
                                if key in {"course_control", "summary", "failures", "model"}
                            }
                            for course in courses
                        },
                    },
                    indent=2,
                )
            )
    except (LookupError, ValueError):
        parser.error(
            "Unknown course, unstarted worker or invalid configuration; inspect status first."
        )
    except SQLAlchemyError:
        parser.error(
            "Database access failed. Check deployment/migrations locally; no resume confirmed."
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
