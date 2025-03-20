from __future__ import annotations

from datetime import datetime
from urllib.parse import urlencode
from uuid import uuid4, UUID

from dotenv import load_dotenv

from fastapi import FastAPI, Request, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import RedirectResponse, HTMLResponse

from pydantic import BaseModel, HttpUrl, Field
from pydantic_ai import Agent

from markdownify import markdownify as html_to_md
from markdown import markdown as md_to_html

load_dotenv()

class CalendarResponse(BaseModel):
    title: str
    start: datetime
    end: datetime
    location: str | None
    details: str | None

    def gcal_url(self, original_url: HttpUrl) -> HttpUrl:
        def format_date(date: datetime) -> str:
            return date.strftime('%Y%m%dT%H%M%SZ')

        gcal_params = {
            "action": "TEMPLATE",
            "text": self.title,
            "dates": f"{format_date(self.start)}/{format_date(self.end)}",
            "location": self.location,
            "details": "\n\n".join([self.details, str(original_url)])
        }
        return HttpUrl(f"https://calendar.google.com/calendar/render?{urlencode(gcal_params)}")


class SummaryResponse(BaseModel):
    title: str = Field(description="A short title (max 4-5 words)")
    summary: str = Field(description="A short Markdown note with relevant sections, sub-sections - each with bulleted and numbered lists and sub-lists.")

    def html(self, url: HttpUrl) -> str:
        return md_to_html(f"# [{self.title}]({str(url)})\n\n{self.summary}")


class Agents:
    calendar = Agent(
        model="gpt-4o",
        result_type=CalendarResponse,
        system_prompt="From the user's input, extract a calendar invite"
    )
    summary = Agent(
        model="gpt-4o",
        result_type=SummaryResponse,
        system_prompt=(
            "Generate a short title and summarize the user's content\n"
            "Summary must be valid markdown; the more structured the document the better\n"
            "Be very short and succinct for each bulleted item.\n"
            "Feel free to include citations or links to products and resources as inline hyperlinks in Markdown.\n"
            "Also, feel free to tabulate in markdown if needed.\n"
            "Ignore disclaimers, self-promotions, acknowledgements etc.\n"
        )
    )

app = FastAPI()

tasks = dict()

async def add_task(fn) -> UUID:
    id = uuid4()
    tasks[id] = asyncio.run(fn())
    return id

@app.post("/calendarize")
async def calendarize(url: HttpUrl, req: Request):
    body = await req.body()
    content = html_to_md(body)
    result = await Agents.calendar.run(f"I have extracted {content=} from {url=}")
    return result.data.gcal_url(url)


@app.get("/result/{id}", name="result")
async def result(id: UUID):
    task = tasks.get(id)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No task with {id=}")
    try:
        result = await task
        breakpoint()
        return result
    except Exception as e:
        breakpoint()
        print(e)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))


@app.post("/summarize")
async def summarize(url: HttpUrl, req: Request):
    body = await req.body()
    content = html_to_md(body)
    result = await Agents.summary.run(f"I have extracted {content=} from {url=}")
    return result.data.html(url)