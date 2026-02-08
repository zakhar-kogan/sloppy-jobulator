from collections import deque
from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.jobs import JobOut


class InMemoryStore:
    """Temporary store for bootstrap endpoints before DB integration lands."""

    def __init__(self) -> None:
        self.discoveries: dict[str, dict] = {}
        self.evidence: dict[str, dict] = {}
        self.jobs: dict[str, dict] = {}
        self.job_queue: deque[str] = deque()
        self.postings: list[dict] = [
            {
                "id": str(uuid4()),
                "title": "Research Assistant in Computational Biology",
                "organization_name": "Example University",
                "canonical_url": "https://example.edu/jobs/ra-computational-biology",
                "status": "active",
                "tags": ["biology", "python"],
                "created_at": datetime.now(timezone.utc),
            }
        ]

    def enqueue_job(self, kind: str, target_type: str, target_id: str | None, inputs: dict) -> str:
        job_id = str(uuid4())
        job = JobOut(
            id=job_id,
            kind=kind,
            target_type=target_type,
            target_id=target_id,
            inputs_json=inputs,
            status="queued",
        ).model_dump()
        self.jobs[job_id] = job
        self.job_queue.append(job_id)
        return job_id


STORE = InMemoryStore()
