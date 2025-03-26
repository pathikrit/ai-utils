from __future__ import annotations

import asyncio
from datetime import datetime
from urllib.parse import urlencode, quote_plus
from uuid import uuid4, UUID
from functools import wraps
import logging
from typing import List, ClassVar, Literal

from dotenv import load_dotenv

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse
from mako.template import Template

from expiringdict import ExpiringDict

from pydantic import BaseModel, HttpUrl, Field
from pydantic_ai import Agent
from litellm import image_generation

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

##################################### Story API ########################################

class ImageTag(BaseModel):
    id: int = Field(description="Image id starting from 1 - I will use this to replace the [[replace_image_X]] tags")
    prompt: str = Field(description="The short prompt for the image that I will feed to the image generation API")

    size: ClassVar[int] = 1024

    def from_llm(self):
        return image_generation(
            model="dall-e-3",
            prompt=f"Generate a Studio Ghibli style story book image for the following prompt: {self.prompt}",
            response_format="url",
            size=f"{ImageTag.size}x{ImageTag.size}",
        )

class Story(BaseModel):
    html: str = Field(description="The story")
    images: List[ImageTag] = Field(description="The images for the story")

    @app.get("/story")
    async def api(prompt: str):
        response = await Agent(
            model="gpt-4o",
            system_prompt=(
                "My 3-year old son Aidan would give a prompt"
                "You must generate an extremely creative and engaging story based on the prompt"
                "Include him in the story also"
                "The returned story must be in a beautiful HTML format with inline CSS"
                "Also include placeholder image tags (2-3) as follows"
                f"<img src='[[replace_image_1]]' width='{ImageTag.size}' height='{ImageTag.size}'/>"
                "Return these tags separately with a short prompt that I would use an AI to generate the images"
                "I will use the [[replace_image_X]] to replace with the image urls from image generation API separately"
            ),
            result_type=Story,
        ).run(prompt)
        story = response.data
        for image in story.images:
            ai_image = image.from_llm()
            story.html = story.html.replace(f"[[replace_image_{image.id}]]", ai_image.data[0].url)
        return HTMLResponse(story.html)