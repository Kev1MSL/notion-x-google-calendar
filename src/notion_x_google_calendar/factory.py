import logging
import datetime
import pytz

from typing import Tuple
from .models import Event, EventHashTable
from notion_module.notion_client import NotionClient
from google_calendar_module.google_calendar_client import GoogleCalendarClient


class EventFactory:
    def __init__(
        self, notion_clt: NotionClient, google_cal_clt: GoogleCalendarClient
    ) -> None:
        self.notion_clt = notion_clt
        self.gcal_clt = google_cal_clt

    def parse_gcal_event(self, gcal_event: dict) -> Event:
        # TODO: Use the .get() method instead of [] and if/else statements
        going = None
        attendees = gcal_event.get("attendees")
        if attendees:
            for attendee in attendees:
                if attendee.get("self"):
                    going = attendee.get("responseStatus")
                break

        event = Event(
            notion_id=None,
            gcal_id=gcal_event["id"],
            name=gcal_event["summary"],
            description=gcal_event["description"]
            if "description" in gcal_event
            else None,
            date_start=gcal_event["start"]["dateTime"],
            date_end=gcal_event["end"]["dateTime"],
            location=gcal_event["location"] if "location" in gcal_event else None,
            calendar_type="Work",
            attendees={attendee["email"] for attendee in gcal_event["attendees"]}
            if "attendees" in gcal_event
            else None,
            meeting_link=gcal_event["hangoutLink"]
            if "hangoutLink" in gcal_event
            else None,
            is_video_conference="conferenceData" in gcal_event,
            going=going,
            organizer=gcal_event["organizer"]["email"]
            if "displayName" not in gcal_event["organizer"]
            else gcal_event["organizer"]["displayName"],
            last_updated=gcal_event["updated"],
        )
        return event

    def parse_notion_event(self, notion_event: dict) -> Event:
        # TODO: Use the .get() method instead of [] and if/else statements
        event = Event(
            notion_id=notion_event["id"],
            gcal_id=None,
            name=notion_event["properties"]["Name"]["title"][0]["plain_text"]
            if notion_event["properties"]["Name"]["title"]
            else None,
            description=notion_event["properties"]["Description"]["rich_text"][0][
                "plain_text"
            ]
            if notion_event["properties"]["Description"]["rich_text"]
            else None,
            date_start=notion_event["properties"]["Date"]["date"]["start"]
            if notion_event["properties"]["Date"]["date"]
            else None,
            date_end=notion_event["properties"]["Date"]["date"]["end"]
            if notion_event["properties"]["Date"]["date"]
            else None,
            location=notion_event["properties"]["Location"]["rich_text"][0][
                "plain_text"
            ]
            if notion_event["properties"]["Location"]["rich_text"]
            else None,
            calendar_type=notion_event["properties"]["Calendar"]["select"]["name"]
            if notion_event["properties"]["Calendar"]["select"]
            else None,
            attendees=set(
                notion_event["properties"]["Attendees"]["rich_text"][0][
                    "plain_text"
                ].split(",")
            )
            if notion_event["properties"]["Attendees"]["rich_text"]
            else None,
            meeting_link=notion_event["properties"]["Meeting Link"]["url"]
            if notion_event["properties"]["Meeting Link"]["url"]
            else None,
            is_video_conference=notion_event["properties"]["Video conference?"][
                "checkbox"
            ],
            going=None,
            organizer=notion_event["properties"]["Organizer"]["rich_text"][0][
                "plain_text"
            ]
            if notion_event["properties"]["Organizer"]["rich_text"]
            else None,
            last_updated=notion_event["last_edited_time"],
        )
        event.is_going_notion = (
            notion_event["properties"]["Going?"]["select"]["name"]
            if notion_event["properties"]["Going?"]["select"]
            else None
        )

        return event

    def build(self) -> Tuple[EventHashTable, EventHashTable]:
        """Builds a list of Events from Notion and Google Calendar, in a formatted way to be used by the synchronizer.

        Returns:
            Tuple[EventHashTable, EventHashTable]: A tuple of two EventHashTable, one for Notion events, and one for Google Calendar events.
        """
        notion_events = self.get_notion_events()
        gcal_events = self.get_google_calendar_events()
        formatted_gcal_events = []
        formatted_notion_events = []

        for notion_event in notion_events:
            event = self.parse_notion_event(notion_event)

            # Skip if the event is in the past
            utc = pytz.utc

            if (
                event.date.end
                and event.date.end.astimezone(utc) < datetime.datetime.now(tz=utc)
            ) or (event.date.start.astimezone(utc) < datetime.datetime.now(tz=utc)):
                continue
            formatted_notion_events.append(event)

        for gcal_event in gcal_events:
            event = self.parse_gcal_event(gcal_event)

            formatted_gcal_events.append(event)

        return EventHashTable(formatted_notion_events), EventHashTable(
            formatted_gcal_events
        )

    def get_notion_events(self) -> list[dict]:
        events = self.notion_clt.list_events()
        if not events:
            logging.warning("No events found in Notion.")
            return []
        return events

    def get_google_calendar_events(self) -> list[dict]:
        now = datetime.datetime.utcnow().isoformat() + "Z"
        events = self.gcal_clt.retrieve_events(now)
        if not events:
            logging.warning("No events found in Google Calendar.")
            return []
        return events
