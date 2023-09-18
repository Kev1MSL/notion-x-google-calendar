import datetime
import logging

import notion_module.notion_client as notion_client
import google_calendar_module.google_calendar_client as gcal_client


class Event:
    def __init__(
        self,
        notion_id,
        gcal_id,
        name,
        description,
        location,
        meeting_link,
        going,
        organizer,
        last_updated,
        date_start,
        attendees,
        calendar_type,  # Synchronize only the events with the property "Calendar" set to "Work"
        date_end=None,
    ):
        self.notion_id = notion_id
        self.gcal_id = gcal_id
        self.name = name
        self.description = description
        self.location = location
        self.last_updated = last_updated
        self.date = Date(date_start, date_end)
        self.meeting_link = meeting_link
        self.going = going
        self.organizer = organizer
        self.attendees = attendees
        self.calendar_type = calendar_type
        self.duration = self.date.duration()

    def __str__(self):
        return f"Event(id = {self.notion_id if self.notion_id else self.gcal_id}, name = {self.name}, description = {self.description}, location = {self.location}, last_updated = {self.last_updated}, date = {self.date}, meeting_link = {self.meeting_link}, going = {self.going}, organizer = {self.organizer}, attendees = {self.attendees}, calendar_type = {self.calendar_type}, duration = {self.duration})"


class Date:
    def __init__(self, start, end=None):
        self.start = datetime.datetime.fromisoformat(start)
        self.end = datetime.datetime.fromisoformat(end) if end is not None else None

    def duration(self):
        if self.end is None:
            return None
        return self.end - self.start

    def __str__(self):
        return f"Date(start = {self.start}, end = {self.end})"


class EventFactory:
    def build(self):
        notion_events = self.get_notion_events()
        gcal_events = self.get_google_calendar_events()
        events = []

        for notion_event in notion_events:
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
                attendees=notion_event["properties"]["Attendees"]["rich_text"][0][
                    "plain_text"
                ].split(",")
                if notion_event["properties"]["Attendees"]["rich_text"]
                else None,
                meeting_link=notion_event["properties"]["Meeting Link"]["url"]
                if notion_event["properties"]["Meeting Link"]["url"]
                else None,
                going=notion_event["properties"]["Going?"]["select"]["name"]
                if notion_event["properties"]["Going?"]["select"]
                else None,
                organizer=notion_event["properties"]["Organizer"]["rich_text"][0][
                    "plain_text"
                ]
                if notion_event["properties"]["Organizer"]["rich_text"]
                else None,
                last_updated=notion_event["last_edited_time"],
            )

            print(event)

            events.append(event)

        for gcal_event in gcal_events:
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
                attendees=[attendee["email"] for attendee in gcal_event["attendees"]]
                if "attendees" in gcal_event
                else None,
                meeting_link=gcal_event["hangoutLink"]
                if "hangoutLink" in gcal_event
                else None,
                going=None,
                organizer=gcal_event["organizer"]["email"]
                if "displayName" not in gcal_event["organizer"]
                else gcal_event["organizer"]["displayName"],
                last_updated=gcal_event["updated"],
            )

            print(event)

            events.append(event)

        return events

    def get_notion_events(self):
        notion_clt = notion_client.NotionClient()
        events = notion_clt.list_events()
        if not events:
            logging.warning("No events found in Notion.")
            return []
        return events

    def get_google_calendar_events(self):
        gcal_clt = gcal_client.GoogleCalendarClient()
        now = datetime.datetime.utcnow().isoformat() + "Z"
        events = gcal_clt.retrieve_events(now)
        if not events:
            logging.warning("No events found in Google Calendar.")
            return []
        return events
