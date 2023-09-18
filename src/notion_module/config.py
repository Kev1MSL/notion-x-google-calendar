import os
from dotenv import load_dotenv

load_dotenv()

_NOTION_API_KEY = os.getenv("NOTION_API_KEY")
_NOTION_CALENDAR_DB_ID = os.getenv("NOTION_CALENDAR_DB_ID")
