import notion_module.notion_client as notion_client
import google_calendar_module.google_calendar_client as gcal_client
import logging

from .app import bi_directionnal_sync


def main():
    # Check if Notion API key and Calendar DB ID are valid
    notion_clt = notion_client.NotionClient()
    if notion_clt.api_key == None or notion_clt.api_key == "":
        logging.error("Notion API key is not set.")
        return
    if notion_clt.calendar_db_id == None or notion_clt.calendar_db_id == "":
        logging.error("No Notion calendar database id is set.")
        return

    # Check if a request to the Notion API can be made
    ret = notion_clt.make_request("GET", f"databases/{notion_clt.calendar_db_id}")
    if ret == None:
        logging.error("Notion API key or DB id is invalid.")
        return

    # Check if Google Calendar API key is valid
    gcal_clt = gcal_client.GoogleCalendarClient()
    if gcal_clt.service == None:
        logging.error("Google Calendar service is not set.")
        return

    bi_directionnal_sync()


if __name__ == "__main__":
    main()
