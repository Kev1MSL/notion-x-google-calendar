from .models import EventFactory


def bi_directionnal_sync():
    event_factory = EventFactory()
    events = event_factory.build()
    # print(events)

    # TODO: Implement bi-directionnal sync
