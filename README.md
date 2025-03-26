# AI Utils
Random collection of AI utils API I use

## Installation
```shell
git clone git@github.com:pathikrit/ai-utils.git
cd ai-utils/
echo "OPENAI_API_KEY=???" >> .env
poetry env use 3.11
poetry install --no-root
```

## Running
```shell
poetry run fastapi dev server.py
```
Then, open <http://localhost:8000/docs>
