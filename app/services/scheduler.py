"""
Scheduler service — wraps APScheduler lifecycle and registers jobs.
The scheduler is started once in app lifespan and shut down on exit.
"""

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import get_settings
from app.database import SessionLocal
from app.logging_config import get_logger
from app.services import escalation_service

logger = get_logger(__name__)

_scheduler = BackgroundScheduler(timezone="UTC")


def _run_escalation_job() -> None:
    """Scheduler callback — creates its own DB session and closes it safely."""
    db = SessionLocal()
    try:
        counts = escalation_service.run_escalation(db)
        logger.info("Scheduled escalation job result: %s", counts)
    except Exception as exc:
        logger.exception("Escalation job failed: %s", exc)
        db.rollback()
    finally:
        db.close()


def start_scheduler() -> None:
    """Start the background scheduler with the escalation job."""
    settings = get_settings()
    interval = settings.escalation_interval_minutes

    _scheduler.add_job(
        _run_escalation_job,
        trigger="interval",
        minutes=interval,
        id="escalation_job",
        replace_existing=True,
        max_instances=1,          # prevent overlap if job runs long
        misfire_grace_time=60,    # tolerate up to 60s of scheduler lag
    )
    _scheduler.start()
    logger.info("Escalation scheduler started (interval=%d min)", interval)


def shutdown_scheduler() -> None:
    """Gracefully stop the scheduler on application shutdown."""
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Escalation scheduler stopped.")


def get_scheduler_status() -> dict:
    """Return current scheduler state for the health/admin endpoint."""
    jobs = _scheduler.get_jobs()
    job_info = []
    for job in jobs:
        job_info.append({
            "id": job.id,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
        })
    return {
        "running": _scheduler.running,
        "jobs": job_info,
    }
