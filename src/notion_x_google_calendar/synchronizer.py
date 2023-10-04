from .models import Event
from .factory import EventFactory
from notion_module.notion_client import NotionClient
from google_calendar_module.google_calendar_client import GoogleCalendarClient
from typing import Tuple
import logging


class Synchronizer:
    def __init__(
        self, notion_clt: NotionClient, google_cal_clt: GoogleCalendarClient
    ) -> None:
        self.notion_clt = notion_clt
        self.google_cal_clt = google_cal_clt
        self.event_factory = EventFactory(
            notion_clt=notion_clt, google_cal_clt=google_cal_clt
        )

    def _send_conference_update(self, notion_id: str, raw_gcal_event: dict) -> None:
        """Send the updated conference link to Notion.

        Args:
            notion_id (str): Notion page id corresponding to the event.
            raw_gcal_event (dict): Raw Google Calendar event comming from the API.
        """
        parsed_gcal_event = self.event_factory.parse_gcal_event(raw_gcal_event)
        parsed_gcal_event.notion_id = notion_id
        self.notion_clt.update_event(notion_event_updated=parsed_gcal_event)

    def bi_directionnal_sync(self) -> None:
        notion_event_hashtable, gcal_event_hashtable = self.event_factory.build()

        # Synchro notion -> gcal, and remove the synced events from the list,
        # only keep the events that need to be synced
        for notion_event_hash in notion_event_hashtable.hash_table:
            # The event exists in both Notion and Google Calendar with same name and date
            # Update the event in case there are changes according to the last_updated field
            if notion_event_hash in gcal_event_hashtable.hash_table:
                notion_event = notion_event_hashtable.hash_table[notion_event_hash]
                gcal_event = gcal_event_hashtable.hash_table[notion_event_hash]

                if notion_event.last_updated > gcal_event.last_updated:
                    notion_event.gcal_id = gcal_event.gcal_id
                    new_gcal_event = self.google_cal_clt.update_event(
                        google_event2update=notion_event
                    )

                    # Check if a new conference needs to be created,
                    # then update the meeting link on Notion
                    if (
                        notion_event.is_video_conference
                        and gcal_event.meeting_link is None
                        and new_gcal_event["hangoutLink"] is not None
                    ):
                        self._send_conference_update(
                            notion_id=notion_event.notion_id,
                            raw_gcal_event=new_gcal_event,
                        )
                        # parsed_gcal_event = self.event_factory.parse_gcal_event(
                        #     new_gcal_event
                        # )
                        # parsed_gcal_event.notion_id = notion_event.notion_id

                        # self.notion_clt.update_event(
                        #     notion_event_updated=parsed_gcal_event
                        # )

                elif notion_event.last_updated < gcal_event.last_updated:
                    gcal_event.notion_id = notion_event.notion_id
                    self.notion_clt.update_event(notion_event_updated=gcal_event)

                else:
                    continue
                del gcal_event_hashtable.hash_table[notion_event_hash]

            # The event exists in Notion but not in Google Calendar
            # Create the event in Google Calendar
            else:
                notion_event = notion_event_hashtable.hash_table[notion_event_hash]
                new_gcal_event = self.google_cal_clt.create_event(notion_event)

                # Check if a new conference needs to be created,
                # then update the meeting link on Notion
                if (
                    notion_event.is_video_conference
                    and new_gcal_event["hangoutLink"] is not None
                ):
                    self._send_conference_update(
                        notion_id=notion_event.notion_id, raw_gcal_event=new_gcal_event
                    )

                    # parsed_gcal_event = self.event_factory.parse_gcal_event(
                    #     new_gcal_event
                    # )
                    # parsed_gcal_event.notion_id = notion_event.notion_id

                    # self.notion_clt.update_event(notion_event_updated=parsed_gcal_event)
        for google_event_hash in gcal_event_hashtable.hash_table:
            # The event exists in Google Calendar but not in Notion

            gcal_event = gcal_event_hashtable.hash_table[google_event_hash]
            new_notion_event = self.notion_clt.create_event(gcal_event)

            # if notion_event.name in gcal_event_hashtable:
            #     gcal_event = gcal_event_hashtable.get_event(notion_event.name)
            #     if notion_event.last_updated > gcal_event.last_updated:
            #         self.event_factory.update_event(notion_event, gcal_event)
            #     elif notion_event.last_updated < gcal_event.last_updated:
            #         self.event_factory.update_event(gcal_event, notion_event)
            #     else:
            #         continue
            #     notion_event_hashtable.remove_event(notion_event)
            #     gcal_event_hashtable.remove_event(gcal_event)

    def make_pair(self, events: list[Event]) -> list[tuple[Event, Event]]:
        pairs = []
        for event in events:
            if event.get_event_type == "notion":
                pair = (event, self.get_corresponding_gcal_event(event, events))
            elif event.get_event_type == "gcal":
                pair = (self.get_corresponding_notion_event(event, events), event)
            else:
                continue
            pairs.append(pair)
        return pairs

    def get_corresponding_notion_event(
        self, gcal_event: Event, events: list[Event]
    ) -> Event:
        for event in events:
            if event.get_event_type == "notion" and event.name == gcal_event.name:
                return event
        return None

    def get_corresponding_gcal_event(
        self, notion_event: Event, events: list[Event]
    ) -> Event:
        for event in events:
            if event.get_event_type == "gcal" and event.name == notion_event.name:
                return event
        return None

    def get_events_to_sync(self, events: list[Event]) -> list[tuple[Event, Event]]:
        return [
            (pair, sync_event[1])
            for pair in self.make_pair(events)
            if (sync_event := self.is_event_to_sync(pair[0], pair[1]))
        ]

    def is_event_to_sync(self, notion_event: Event, gcal_event: Event):
        """Check whether a pair of event needs to be synchronized or not, and returns the event to be synchronized on.

        Args:
            self (EventFactory): EventFactory instance.
            notion_event (Event): Notion event.
            gcal_event (Event): Google Calendar event.

        Returns:
            Tuple(bool, Event): A tuple containing a boolean and an event.
        """
        if notion_event is None:
            return True, gcal_event

        if gcal_event is None:
            return True, notion_event

        if notion_event.last_updated > gcal_event.last_updated:
            return True, notion_event

        if notion_event.last_updated < gcal_event.last_updated:
            return True, gcal_event

        return None
