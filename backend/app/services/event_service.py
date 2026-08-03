import requests
from datetime import datetime, timezone


EVENT_API = (
    "http://127.0.0.1:9000/chart/event"
)


def record_event(
        strategy,
        pair,
        trade_id,
        event_type,
        side,
        price,
        amount,
        message="",
        current_time=None
):

    try:

        if current_time:

            event_dt = current_time

        else:

            event_dt = datetime.now(
                timezone.utc
            )


        requests.post(

            EVENT_API,

            json={

                "strategy":strategy,

                "pair":pair,

                "trade_id":trade_id,

                "event_type":event_type,

                "side":side,

                "price":price,

                "amount":amount,

                "time":
                    event_dt.isoformat(),

                "candle_time":
                    event_dt.isoformat(),

                "message":message

            },

            timeout=1

        )


    except Exception as e:

        print(
            "record event error:",
            e
        )