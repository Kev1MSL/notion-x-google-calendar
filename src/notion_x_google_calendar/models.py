import datetime


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
    ) -> None:
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

    def __str__(self) -> str:
        return f"Event(id = {self.notion_id if self.notion_id else self.gcal_id}, name = {self.name}, description = {self.description}, location = {self.location}, last_updated = {self.last_updated}, date = {self.date}, meeting_link = {self.meeting_link}, going = {self.going}, organizer = {self.organizer}, attendees = {self.attendees}, calendar_type = {self.calendar_type}, duration = {self.duration})"

    @property
    def get_event_type(self) -> str:
        if self.notion_id:
            return "notion"
        elif self.gcal_id:
            return "gcal"
        else:
            return None


class Date:
    def __init__(self, start, end=None) -> None:
        self.start = datetime.datetime.fromisoformat(start)
        self.end = datetime.datetime.fromisoformat(end) if end is not None else None

    def duration(self) -> datetime.timedelta:
        if self.end is None:
            return None
        return self.end - self.start

    def __str__(self) -> str:
        return f"Date(start = {self.start}, end = {self.end})"


class EventHashTable:
    def __init__(self, events: list[Event]) -> None:
        self.events = events
        self.hash_table = self.build_hash_table()

    def build_hash_table(self) -> dict[int, Event]:
        hash_table = {}
        for event in self.events:
            # Hash the event name and the event date to get a unique key
            key = hash((event.name, event.date.start))
            hash_table[key] = event
        return hash_table

    def get_event(self, event_name: str, start_date: datetime) -> Event:
        return self.hash_table.get(hash((event_name, start_date)), None)
