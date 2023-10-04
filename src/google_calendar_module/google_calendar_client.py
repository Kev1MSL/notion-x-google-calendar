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

    def _get_user_email(self) -> str:
        return self.service.calendarList().get(calendarId="primary").execute()["id"]

    def _build_attendees_list(self, attendees: set[str], event: Event) -> list[dict]:
        user_email = self._get_user_email()
        if not attendees:
            return None
        attendees2add = attendees.copy()
        attendees2add.add(user_email)
        return [
            {"email": attendee.strip(), "responseStatus": event.going}
            if attendee.strip() == user_email
            else {"email": attendee.strip()}
            for attendee in attendees2add
        ]

    def create_event(self, new_event: Event) -> dict:
        """Create a new event in Google Calendar.

        Args:
            new_event (Event): Notion event to add in Google Calendar

        Returns:
            dict: The created event from Google Calendar as a dict.
        """

        event = {
            "summary": new_event.name,
            "location": new_event.location,
            "description": new_event.description,
            "start": {
                "dateTime": new_event.date.start.isoformat(),
            },
            "end": {
                "dateTime": new_event.date.end.isoformat(),
            },
            "attendees": self._build_attendees_list(new_event.attendees, new_event),
            "reminders": {"useDefault": True},
        }

        update_conference = 0

        if new_event.is_video_conference:
            event["conferenceData"] = {
                "createRequest": {
                    # Use notion_id as requestId to generate a unique conference id
                    "requestId": new_event.notion_id,
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            }
            update_conference = 1

        ret = (
            self.service.events()
            .insert(
                calendarId=self.calendar_id,
                body=event,
                conferenceDataVersion=update_conference,
                sendUpdates="all",
            )
            .execute()
        )

        return ret

    def update_event(self, google_event2update: Event) -> dict:
        """Update the event in Google Calendar.

        Args:
            google_event2update (Event): Notion event to update in Google Calendar.

        Returns:
            dict: The updated event from Google Calendar as a dict.
        """
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

        # Update the attendees list
        event2update["attendees"] = self._build_attendees_list(
            google_event2update.attendees, google_event2update
        )

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
