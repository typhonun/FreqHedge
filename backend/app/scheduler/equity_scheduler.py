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
        trigger='interval',
        seconds=5,
        id='record_history_job',
        max_instances=1,  # 确保同一时间只有一个任务
        coalesce=True,  # ★ 如果因为卡顿错过多次，只补跑一次，不堆积
        misfire_grace_time=15,  # ★ 允许最大延迟秒数（15秒内没跑的任务照样执行）
        replace_existing=True
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