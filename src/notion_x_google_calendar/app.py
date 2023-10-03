from notion_x_google_calendar.synchronizer import Synchronizer
import logging


def bi_directionnal_sync(notion_client, google_cal_client):
    # event_factory = EventFactory(
    #     notion_clt=notion_client, google_cal_clt=google_cal_client
    # )
    # notion_events, gcal_events = event_factory.build()

    # TODO: Implement bi-directionnal sync

    synchronizer = Synchronizer(
        notion_clt=notion_client, google_cal_clt=google_cal_client
    )

    logging.info("Synchronizing events...")
    synchronizer.bi_directionnal_sync()
