from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.services.position_service import PositionService


scheduler = BackgroundScheduler()


def record_history_job():

    try:

        PositionService.record_metrics()

    except Exception as e:

        print(
            "history scheduler error:",
            e
        )


def start_scheduler():

    # 启动时立即记录一次
    record_history_job()

    scheduler.add_job(

        record_history_job,

        trigger=IntervalTrigger(seconds=5),

        id="record_history",

        replace_existing=True,

        max_instances=1,

        coalesce=True

    )

    scheduler.start()

    print(
        "History scheduler started."
    )


def stop_scheduler():

    scheduler.shutdown()

    print(
        "History scheduler stopped."
    )