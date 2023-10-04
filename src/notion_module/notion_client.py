import logging

from .config import _NOTION_API_KEY, _NOTION_CALENDAR_DB_ID
from .utils import METHODS
from notion_x_google_calendar.models import Event


class NotionClient:
    def __init__(
        self, api_key=_NOTION_API_KEY, calendar_db_id=_NOTION_CALENDAR_DB_ID
    ) -> None:
        self.api_key = api_key
        self.calendar_db_id = calendar_db_id

    def make_request(self, method, endpoint, body=None) -> dict:
        authorization = f"Bearer {self.api_key}"
        headers = {
            "Authorization": authorization,
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28",
        }
        url = f"https://api.notion.com/v1/{endpoint}"
        response = METHODS[method](url, headers=headers, json=body)
        if response.status_code != 200:
            raise Exception(f"Error: {response.status_code}. {response.text}")
        return response.json()

    def list_events(self) -> list[dict]:
        try:
            events = self.make_request(
                "POST", f"databases/{self.calendar_db_id}/query"
            )["results"]
            return events
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            return None

    def update_event(self, notion_event_updated: Event) -> None:
        # Default body initialization
        body = {
            "properties": {
                "Name": {"title": [{"text": {"content": notion_event_updated.name}}]},
                "Description": {"rich_text": [{"text": {"content": ""}}]},
                "Date": {"date": {"start": None, "end": None}},
                "Duration (mins)": {"number": None},
                "Location": {"rich_text": [{"text": {"content": ""}}]},
                "Calendar": {"select": {"name": None}},
                "Attendees": {"rich_text": [{"text": {"content": ""}}]},
                "Video conference?": {"checkbox": False},
                "Meeting Link": {"url": None},
                "Going?": {"select": {"name": None}},
                "Organizer": {"rich_text": [{"text": {"content": ""}}]},
            }
        }

        if notion_event_updated.description:
            body["properties"]["Description"] = {
                "rich_text": [{"text": {"content": notion_event_updated.description}}]
            }
        if notion_event_updated.date.start:
            body["properties"]["Date"] = {
                "date": {"start": notion_event_updated.date.start.isoformat()}
            }

        if notion_event_updated.date.end:
            body["properties"]["Date"]["date"][
                "end"
            ] = notion_event_updated.date.end.isoformat()

        if notion_event_updated.duration:
            body["properties"]["Duration (mins)"] = {
                "number": notion_event_updated.duration.total_seconds() / 60
            }

        if notion_event_updated.location:
            body["properties"]["Location"] = {
                "rich_text": [{"text": {"content": notion_event_updated.location}}]
            }

        if notion_event_updated.calendar_type:
            body["properties"]["Calendar"] = {
                "select": {"name": notion_event_updated.calendar_type}
            }

        if notion_event_updated.attendees:
            body["properties"]["Attendees"] = {
                "rich_text": [
                    {"text": {"content": ", ".join(notion_event_updated.attendees)}}
                ]
            }

        body["properties"]["Video conference?"] = {
            "checkbox": notion_event_updated.is_video_conference
        }

        if notion_event_updated.meeting_link:
            body["properties"]["Meeting Link"] = {
                "url": notion_event_updated.meeting_link
            }

        if notion_event_updated.going:
            body["properties"]["Going?"] = {
                "select": {"name": notion_event_updated.is_going_notion}
            }

        if notion_event_updated.organizer:
            body["properties"]["Organizer"] = {
                "rich_text": [{"text": {"content": notion_event_updated.organizer}}]
            }

        try:
            ret = self.make_request(
                "PATCH", f"pages/{notion_event_updated.notion_id}", body=body
            )
            print(ret)
        except Exception as e:
            logging.error(f"An error occurred: {e}")
