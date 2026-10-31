from datetime import date
from apscheduler.schedulers.background import BackgroundScheduler
from app.core.database import SessionLocal
from app.models import Subscription, Plan, AuditLog

scheduler = BackgroundScheduler()


def auto_close_expired_subscriptions():
    db = SessionLocal()
    try:
        today = date.today()
        expired_subs = (
            db.query(Subscription)
            .join(Subscription.plan)
            .filter(
                Subscription.status == "active",
                Subscription.end_date <= today,
                Plan.auto_close == True,
            )
            .all()
        )
        for sub in expired_subs:
            sub.status = "closed"
            log = AuditLog(
                entity_type="subscription",
                entity_id=sub.id,
                action="auto_closed_on_expiration",
                old_value={"status": "active"},
                new_value={"status": "closed"},
                user_id=None,
            )
            db.add(log)
        if expired_subs:
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def start_scheduler():
    scheduler.add_job(auto_close_expired_subscriptions, "interval", hours=1)
    scheduler.start()


def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown()
