import datetime
import os.path
import logging
import uuid

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

    def update_event(self, google_event2update: Event) -> dict:
        event2update = (
            self.service.events()
            .get(calendarId=self.calendar_id, eventId=google_event2update.gcal_id)
            .execute()
        )

        event2update["start"]["dateTime"] = google_event2update.date.start.isoformat()
        event2update["end"]["dateTime"] = google_event2update.date.end.isoformat()

        event2update["summary"] = google_event2update.name
        event2update["description"] = google_event2update.description
        event2update["location"] = google_event2update.location

        # Find the user's email in the attendees list
        my_email = ""
        if event2update["attendees"]:
            for attendee in event2update["attendees"]:
                if attendee.get("self"):
                    my_email = attendee.get("email")
                    break

        # Update the attendees list
        event2update["attendees"] = [
            {"email": attendee.strip(), "responseStatus": google_event2update.going}
            if attendee.strip() == my_email
            else {"email": attendee.strip()}
            for attendee in google_event2update.attendees
        ]

        # Update the conferenceDataVersion to let Google know that the conference has
        # been updated
        update_conference = 0

        if (
            "conferenceData" in event2update
            and not google_event2update.is_video_conference
        ):
            del event2update["conferenceData"]
            if "hangoutLink" in event2update:
                del event2update["hangoutLink"]

            update_conference = 1

        # Create a conference if the event is a video conference from Notion
        elif (
            "conferenceData" not in event2update
            and google_event2update.is_video_conference
        ):
            event2update["conferenceData"] = {
                "createRequest": {
                    # Use notion_id as requestId to generate a unique conference id
                    "requestId": google_event2update.notion_id,
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            }
            update_conference = 1

        ret = (
            self.service.events()
            .update(
                calendarId=self.calendar_id,
                eventId=google_event2update.gcal_id,
                body=event2update,
                conferenceDataVersion=update_conference,
                sendUpdates="all",
            )
            .execute()
        )

        return ret


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
