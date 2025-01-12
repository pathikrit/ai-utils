# AI Utils
Random collection of AI utls API I use

## Installation
```shell
git clone git@github.com:pathikrit/ai-utils.git
cd ai-utils/

echo "PORT=3000
OPENAI_API_KEY=???" >> .env

npm install
```

## Running
```shell
node --watch index.js
```

## APIs
- `GET /summarize?url=`
- `POST /summarize?url=` (with body = HTML of the page)
- `GET /calendarize?url=`
- `POST /calendarize?url=` (with body = HTML of the page)

## API Examples
* Summarize: <http://localhost:3000/summarize?url=https://www.federalreserve.gov/newsevents/speech/bernanke20130301a.htm>
* Calendarize: <http://localhost:3000/summarize?url=https://wbf.app.neoncrm.com/np/clients/wbf/event.jsp?event=6111>