# AI Utils
Random collection of AI utils API I use

## Installation
```shell
git clone git@github.com:pathikrit/ai-utils.git
cd ai-utils/

echo "OPENAI_API_KEY=???" >> .env

poetry install --no-root
```

## Running
```shell
poetry run fastapi dev server.py
```

## APIs
- `POST /summarize?url=` (with body = HTML of the page)
- `POST /calendarize?url=` (with body = HTML of the page)

