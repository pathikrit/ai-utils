# AI Utils
Random collection of AI utls API I use

## Installation
```
git clone git@github.com:pathikrit/ai-utils.git
cd ai-utils/

echo "PORT=3000
OPENAI_API_KEY=???" >> .env

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

Summary Example: <http://localhost:3000/summarize?url=https://www.federalreserve.gov/newsevents/speech/bernanke20130301a.htm>
Calendarize Example: <https://wbf.app.neoncrm.com/np/clients/wbf/event.jsp?event=6111>