from datetime import datetime

from fastapi import FastAPI, Request
from urllib.parse import urlencode
from pydantic import BaseModel, HttpUrl

app = FastAPI()

@app.get("/")
async def main_route():
    event = CalendarResponse(
        title="Meeting",
        start=datetime(2025, 3, 17, 10, 0),
        end=datetime(2025, 3, 17, 11, 0),
        location="New York",
        details="Project discussion"
    )
    return {"message": event.gcal_url()}


@app.post("/calendarize")
async def read_body(req: Request):
    return {"raw_body": req.body}

class CalendarResponse(BaseModel):
    title: str
    start: datetime
    end: datetime
    location: str
    details: str

    def gcal_url(self) -> HttpUrl:
        def format_date(date: datetime) -> str:
            return date.strftime('%Y%m%dT%H%M%SZ')

        gcal_base_url = "https://calendar.google.com/calendar"
        gcal_params = {
            "action": "TEMPLATE",
            "text": self.title,
            "dates": f"{format_date(self.start)}/{format_date(self.end)}",
            "location": self.location,
            "details": self.details
        }
        return HttpUrl(f"{gcal_base_url}/render?{urlencode(gcal_params)}")
