from __future__ import annotations

from datetime import datetime
from urllib.parse import urlencode

from fastapi import FastAPI, Request, Depends
from dotenv import load_dotenv

from pydantic import BaseModel, HttpUrl, computed_field
from pydantic_ai import Agent
from markdownify import markdownify as md

load_dotenv()

class CalendarResponse(BaseModel):
    title: str
    start: datetime
    end: datetime
    location: str | None
    details: str | None

    @computed_field
    @property
    def gcal_url(self) -> HttpUrl:
        def format_date(date: datetime) -> str:
            return date.strftime('%Y%m%dT%H%M%SZ')

        gcal_params = {
            "action": "TEMPLATE",
            "text": self.title,
            "dates": f"{format_date(self.start)}/{format_date(self.end)}",
            "location": self.location,
            "details": self.details
        }
        return HttpUrl(f"https://calendar.google.com/calendar/render?{urlencode(gcal_params)}")

calendar_agent = Agent(
    model="gpt-4o",
    result_type=CalendarResponse,
    system_prompt="From the user's input, extract a calendar invite"
)

app = FastAPI()

async def html_to_markdown_middleware(req: Request) -> str:
    body = await req.body()
    return md(body)

@app.post("/calendarize")
async def calendarize(url: HttpUrl, content: str =  Depends(html_to_markdown_middleware)):
    result = await calendar_agent.run(f"I have extracted {content=} from {url=}")
    return result.data
