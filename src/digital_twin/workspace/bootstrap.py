"""Batch only the deterministic comparison baseline during offline preparation."""

from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from .llm import predict_rules
from .models import Analysis, AnalysisJob


def prepare_baselines(store, progress=print):
    """Complete queued baseline jobs in bounded transactions, never claim LLM jobs.

    Active workers' running jobs are left untouched. Conditional updates and result
    insertion share a transaction, so a restart cannot install a partial result.
    """
    count = 0
    policies = {}
    while True:
        with Session(store.engine) as session:
            jobs = session.scalars(
                select(AnalysisJob)
                .where(AnalysisJob.model_kind == "baseline", AnalysisJob.status == "queued")
                .order_by(AnalysisJob.created_at)
                .limit(100)
            ).all()
            inputs = [(job.id, job.state_id, job.policy_version) for job in jobs]
        if not inputs:
            return count
        results = []
        for job_id, state_id, version in inputs:
            state = store.get_snapshot(state_id)
            key = (state.presentation_id, version)
            if key not in policies:
                policies[key] = store.get_policy(*key)
            result = predict_rules(state, policies[key])
            result.update(
                policy_version=version,
                state_id=state_id,
                job_id=job_id,
                model_kind="baseline",
                generated_at=datetime.now(UTC).isoformat(),
            )
            results.append((job_id, state_id, version, result))
        with Session(store.engine) as session, session.begin():
            for job_id, state_id, version, result in results:
                moment = datetime.now(UTC)
                updated = session.execute(
                    update(AnalysisJob)
                    .where(AnalysisJob.id == job_id, AnalysisJob.status == "queued")
                    .values(
                        status="abstained" if result["output"]["abstain"] else "validated",
                        attempts=AnalysisJob.attempts + 1,
                        updated_at=moment,
                    )
                )
                if updated.rowcount == 1:
                    session.add(
                        Analysis(
                            id=job_id,
                            state_id=state_id,
                            policy_version=version,
                            model_kind="baseline",
                            payload=result,
                            created_at=moment,
                        )
                    )
                    count += 1
        if count and count % 500 == 0:
            progress(f"Completed comparison jobs: {count}")
