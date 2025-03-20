from __future__ import annotations

import asyncio
from datetime import datetime
from urllib.parse import urlencode
from uuid import uuid4, UUID
from functools import wraps

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

    @classmethod
    def from_llm(cls, url: HttpUrl, markdown: str):
        return Agent(
            model="gpt-4o",
            result_type=cls,
            system_prompt="From the user's input, extract a calendar invite"
        ).run(f"I have extracted {markdown=} from {url=}")

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

    def to_html(self, url: HttpUrl) -> str:
        return md_to_html(f"# [{self.title}]({str(url)})\n\n{self.summary}")


app = FastAPI()

tasks = dict()

def background_task(fn):
    @wraps(fn)
    async def wrapper(*args, **kwargs):
        req = kwargs.get("req")
        async def task_fn():
            return await fn(*args, **kwargs)
        task_id: UUID = uuid4()
        tasks[task_id] = asyncio.create_task(task_fn())
        return req.url_for("result", id=task_id)
    return wrapper

@app.get("/result/{id}", name="result")
async def result(id: UUID):
    if id not in tasks:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No task with {id=}")
    try:
        return await tasks[id]
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))

async def body_to_md_middleware(req: Request) -> str:
    html = await req.body()
    return html_to_md(html)

@app.post("/calendarize")
@background_task
async def calendarize(url: HttpUrl, req: Request, markdown: str = Depends(body_to_md_middleware)):
    result = await Calendar.from_llm(url=url, markdown=markdown)
    return RedirectResponse(result.data.gcal_url(url))


@app.post("/summarize")
@background_task
async def summarize(url: HttpUrl, req: Request, markdown: str = Depends(body_to_md_middleware)):
    result = await Summary.from_llm(url=url, markdown=markdown)
    return HTMLResponse(result.data.to_html(url))
