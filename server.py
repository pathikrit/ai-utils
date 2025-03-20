from __future__ import annotations

import asyncio
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

class Calendar(BaseModel):
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


class Summary(BaseModel):
    title: str = Field(description="A short title (max 4-5 words)")
    summary: str = Field(description="A short Markdown note with relevant sections, sub-sections - each with bulleted and numbered lists and sub-lists.")

    def html(self, url: HttpUrl) -> str:
        return md_to_html(f"# [{self.title}]({str(url)})\n\n{self.summary}")


class Agents:
    calendar = Agent(
        model="gpt-4o",
        result_type=Calendar,
        system_prompt="From the user's input, extract a calendar invite"
    )
    summary = Agent(
        model="gpt-4o",
        result_type=Summary,
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

def background_task(fn) -> UUID:
    id = uuid4()
    tasks[id] = asyncio.create_task(fn())
    return id

@app.get("/result/{id}", name="result")
async def result(id: UUID):
    if id not in tasks:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No task with {id=}")
    try:
        return await tasks[id]
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

@app.post("/calendarize")
async def calendarize(url: HttpUrl, req: Request):
    html = await req.body()
    async def fn():
        prompt = f"I have extracted content={html_to_md(html)} from {url=}"
        result = await Agents.calendar.run(prompt)
        return RedirectResponse(result.data.gcal_url(url))
    return req.url_for("result", id=background_task(fn))


@app.post("/summarize")
async def summarize(url: HttpUrl, req: Request):
    html = await req.body()
    async def fn():
        prompt = f"I have extracted content={html_to_md(html)} from {url=}"
        result = await Agents.summary.run(prompt)
        return HTMLResponse(result.data.html(url))
    return req.url_for("result", id=background_task(fn))
