# AI Utils
Random collection of AI utls API I use

## Installation
```
git clone git@github.com:pathikrit/ai-utils.git
cd ai-utils/

echo "PORT=3000
GEMINI_API_KEY=???" >> .env

npm install
```

## Running
```
node --watch index.js
```

## APIs

- `GET /summarize?url=`
- `POST /summarize?url=` (with body = HTML of the page)
- `GET /calendarize?url=`
- `POST /calendarize?url=` (with body = HTML of the page)

Usage Example: <http://localhost:3000/summarize?url=https://www.whattoexpect.com/toddler/behavior/potty-training-problem-refusing-to-poop.aspx>