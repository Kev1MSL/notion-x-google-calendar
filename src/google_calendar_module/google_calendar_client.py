import datetime
import os.path
import logging

from notion_x_google_calendar.models import Event

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]


class GoogleCalendarClient:
    def __init__(self, calendar_id="primary") -> None:
        def run_flow():
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
            return creds

        ## Authentication ##
        creds = None

        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except:
                    logging.error("Google Calendar API token is invalid.")
                    logging.info("Deleting token.json file, and trying again...")
                    os.remove("token.json")
                    creds = run_flow()
            else:
                creds = run_flow()
            # Save the credentials for the next run
            with open("token.json", "w") as token:
                token.write(creds.to_json())

        ## Google Calendar Service ##
        self.service = build("calendar", "v3", credentials=creds)
        self.calendar_id = calendar_id

    def retrieve_events(
        self, time_min, max_results=10, single_events=True, order_by="startTime"
    ) -> list[dict]:
        page_token = None
        events = []
        try:
            # Read all the pages of events from the calendar API
            while True:
                event_results = (
                    self.service.events()
                    .list(
                        calendarId=self.calendar_id,
                        pageToken=page_token,
                        timeMin=time_min,
                        maxResults=max_results,
                        singleEvents=single_events,
                        orderBy=order_by,
                    )
                    .execute()
                )
                events += event_results.get("items", [])
                page_token = event_results.get("nextPageToken")

                # Arrived at the last page
                if not page_token:
                    break

            return events
        except HttpError as error:
            logging.error(
                "An HTTP error %d occurred:\n%s" % (error.resp.status, error.content)
            )
            return None

    def update_event(google_event2update: Event) -> None:
        return NotImplemented


def main() -> None:
    google_cal_client = GoogleCalendarClient()
    now = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
    events = google_cal_client.retrieve_events(now)
    if not events:
        print("No upcoming events found.")
        return
    for event in events:
        start = event["start"].get("dateTime", event["start"].get("date"))
        print(start, event["summary"])
