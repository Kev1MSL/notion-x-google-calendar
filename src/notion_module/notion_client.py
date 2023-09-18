import logging

from .config import _NOTION_API_KEY, _NOTION_CALENDAR_DB_ID
from .utils import METHODS


class NotionClient:
    def __init__(self, api_key=_NOTION_API_KEY, calendar_db_id=_NOTION_CALENDAR_DB_ID):
        self.api_key = api_key
        self.calendar_db_id = calendar_db_id

    def make_request(self, method, endpoint, body=None):
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

    def list_events(self):
        try:
            events = self.make_request(
                "POST", f"databases/{self.calendar_db_id}/query"
            )["results"]
            return events
        except Exception as e:
            logging.error(f"An error occurred: {e}")
            return None
