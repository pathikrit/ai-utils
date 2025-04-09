from __future__ import annotations

import asyncio
from datetime import datetime
from urllib.parse import urlencode, quote_plus
from uuid import uuid4, UUID
from functools import wraps
import logging
from typing import List, ClassVar, Literal
import json

from dotenv import load_dotenv

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse
from mako.template import Template

from expiringdict import ExpiringDict

from pydantic import BaseModel, HttpUrl, Field, Json
from pydantic_ai import Agent

from markdownify import markdownify as html_to_md
from markdown import markdown as md_to_html

##################################### Setup globals ########################################

load_dotenv()
log = logging.getLogger(__name__)

app = FastAPI()
tasks = ExpiringDict(max_age_seconds=60*60, max_len=100_000)

######################################### Server ##############################################

class Server:
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

    @app.get("/")
    async def root():
        with open("README.md", "r", encoding="utf-8") as f:
            markdown = f.read()
        return HTMLResponse(md_to_html(markdown))

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
    @Server.background_task
    async def api(url: HttpUrl, req: Request, markdown: str = Depends(Server.body_to_md_middleware)):
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
    @Server.background_task
    async def api(url: HttpUrl, req: Request, markdown: str = Depends(Server.body_to_md_middleware)):
        result = await Summary.from_llm(url=url, markdown=markdown)
        return HTMLResponse(result.data.to_html(url))

    def to_html(self, url: HttpUrl) -> str:
        return md_to_html(f"# [{self.title}]({str(url)})\n\n{self.summary}")

##################################### Restaurant API ########################################

class Restaurant(BaseModel):
    name: str = Field(description="Name of the restaurant (or bar, cafe, etc.)")
    location: str | None = Field(description="City or neighborhood name e.g. 'West Village' or 'Brooklyn' or 'NYC' or 'Austin, TX'")
    type: Literal["Restaurant", "Bar", "Cafe"] = Field(description="Type of establishment")

    @classmethod
    def from_llm(cls, url: HttpUrl, markdown: str):
        return Agent(
            model="gpt-4o",
            result_type=List[cls],
            system_prompt="Extract all restaurants mentioned in the user's input"
        ).run(f"I have extracted {markdown=} from {url=}")

    @app.post("/restaurantize")
    @Server.background_task
    async def api(url: HttpUrl, req: Request, markdown: str = Depends(Server.body_to_md_middleware)):
        result = await Restaurant.from_llm(url=url, markdown=markdown)
        html = Restaurant.html.render(restaurants=result.data, original_url=url)
        return HTMLResponse(html)

    html: ClassVar[Template] = Template("""
<% from urllib.parse import quote_plus %>
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Restaurants</title>
  <script type="text/javascript">
    window.onload = () => document
      .querySelectorAll("a.multi-open")
      .forEach(link => window.open(link.href, '_blank'));
  </script>
</head>
<body>
  <h1><a href="${original_url}" target="_blank">Restaurants</a></h1>
  <ol>
    % for restaurant in restaurants:
      <%
         text = " ".join([restaurant.name, restaurant.location or "", restaurant.type])
         link = "https://www.google.com/search?q=" + quote_plus(text)
      %>
      <li><a class="multi-open" href="${link}" target="_blank">${restaurant.name}</a></li>
    % endfor
  </ol>
</body>
</html>
""")

##################################### Tabs API ########################################

class TabGroup(BaseModel):
    group: str = Field(description="Name of the group - short single word")
    tabIds: List[int] = Field(description="Set of tab ids in this group")

    @classmethod
    def from_llm(cls, tabs: Json):
        return Agent(
            model="gpt-4o",
            result_type=List[cls],
            system_prompt=(
                "The user will provide a list of open tabs (id, url, page title)\n"
                "Group them into DISTINCT groups and provide a short name for each group\n"
                'e.g. "coding", "finance", "travel", "news", "shopping", "amazon", "ai" etc.\n'
                "but feel free to create your own group names too.\n"
                "If there are bunch of pages from same domain, then maybe just create a category with the domain name\n"
                "unless its something like Google or ChatGPT - then group based on what I am searching (see the page title)\n"
                "In general, rely on page title more than the domain\n",
                "If any page looks like tickets (for movies, shows or activities)\n"
                "or reservations (for restaurants & bars) use the category 'date night'"
            )
        ).run(json.dumps(tabs))

    @app.post("/tabolate")
    async def api(req: Request):
        tabs = await req.json()
        result = await TabGroup.from_llm(tabs)
        data = result.data

        valid_tab_ids = {tab["tabId"] for tab in tabs}
        new_groups = []

        for tab_group in data:
            tab_group.tabIds = set(tab_group.tabIds) & valid_tab_ids
            if len(tab_group.tabIds) > 1:
                new_groups.append(tab_group)
                valid_tab_ids -= tab_group.tabIds

        return new_groups
