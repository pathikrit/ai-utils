# Webpage Summarizer
Trivial webapp to summarize webpages

## Installation
```
git clone git@github.com:pathikrit/webpage-summarizer.git
cd webpage-summarizer/

echo "PORT=3000
GEMINI_API_KEY=???" >> .env

npm install
```

## Running
```
node --watch index.js
```

Usage Example: <http://localhost:3000/summarize?url=https://www.whattoexpect.com/toddler/behavior/potty-training-problem-refusing-to-poop.aspx>