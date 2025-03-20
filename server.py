from __future__ import annotations

import asyncio
from datetime import datetime
from urllib.parse import urlencode
from uuid import uuid4, UUID
from functools import wraps
import logging
from typing import List

from dotenv import load_dotenv

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse

from expiringdict import ExpiringDict

from pydantic import BaseModel, HttpUrl, Field
from pydantic_ai import Agent

from markdownify import markdownify as html_to_md
from markdown import markdown as md_to_html

##################################### Setup globals ########################################

load_dotenv()
log = logging.getLogger(__name__)

app = FastAPI()
tasks = ExpiringDict(max_age_seconds=60*60, max_len=100_000)

##################################### Server utils ########################################
def background_task(fn):
    """Decorator to run fn in the background task and return a URL to check the result"""
    @wraps(fn)
    async def wrapper(*args, **kwargs):
        req = kwargs.get("req")
        async def task_fn():
            return await fn(*args, **kwargs)
        task_id = uuid4()
        tasks[task_id] = asyncio.create_task(task_fn())
        return req.url_for("result", id=task_id)
    return wrapper

async def body_to_md_middleware(req: Request) -> str:
    html = await req.body()
    return html_to_md(html)

@app.get("/result/{id}", name="result")
async def result(id: UUID):
    if id not in tasks:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No task found")
    try:
        return await tasks[id]
    except Exception as e:
        log.error(f"Failed to execute task {id=}", e)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Task failed: {e}")

##################################### Calendar API ########################################

class Calendar(BaseModel):
    title: str
    start: datetime
    end: datetime
    location: str | None
    details: str | None

    @classmethod
    def from_llm(cls, url: HttpUrl, markdown: str):
        return Agent(
            model="gpt-4o",
            result_type=cls,
            system_prompt="From the user's input, extract a calendar invite"
        ).run(f"I have extracted {markdown=} from {url=}")

    @app.post("/calendarize")
    @background_task
    async def api(url: HttpUrl, req: Request, markdown: str = Depends(body_to_md_middleware)):
        result = await Calendar.from_llm(url=url, markdown=markdown)
        return RedirectResponse(result.data.gcal_url(url))

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

##################################### Summary API ########################################

class Summary(BaseModel):
    title: str = Field(description="A short title (max 4-5 words)")
    summary: str = Field(description="A short Markdown note with relevant sections, sub-sections - each with bulleted and numbered lists and sub-lists.")

    @classmethod
    def from_llm(cls, url: HttpUrl, markdown: str):
        return Agent(
            model="gpt-4o",
            result_type=cls,
            system_prompt=(
                "Generate a short title and summarize the user's content\n"
                "Summary must be valid markdown; the more structured the document the better\n"
                "Be very short and succinct for each bulleted item.\n"
                "Feel free to include citations or links to products and resources as inline hyperlinks in Markdown.\n"
                "Also, feel free to tabulate in markdown if needed.\n"
                "Ignore disclaimers, self-promotions, acknowledgements etc.\n"
            )
        ).run(f"I have extracted {markdown=} from {url=}")

    @app.post("/summarize")
    @background_task
    async def api(url: HttpUrl, req: Request, markdown: str = Depends(body_to_md_middleware)):
        result = await Summary.from_llm(url=url, markdown=markdown)
        return HTMLResponse(result.data.to_html(url))

    def to_html(self, url: HttpUrl) -> str:
        return md_to_html(f"# [{self.title}]({str(url)})\n\n{self.summary}")

##################################### Restaurant API ########################################

class Restaurant(BaseModel):
    name: str = Field(description="Name of the restaurant (or bar, cafe, etc.)")
    location: str | None = Field(description="City or neighborhood name e.g. 'West Village' or 'Brooklyn' or 'NYC' or 'Austin, TX'")

    @classmethod
    def from_llm(cls, url: HttpUrl, markdown: str):
        return Agent(
            model="gpt-4o",
            result_type=List[cls],
            system_prompt="Extract all restaurants mentioned in the user's input"
        ).run(f"I have extracted {markdown=} from {url=}")

    @app.post("/restaurantize")
    @background_task
    async def api(url: HttpUrl, req: Request, markdown: str = Depends(body_to_md_middleware)):
        result = await Restaurant.from_llm(url=url, markdown=markdown)
        return result.data
