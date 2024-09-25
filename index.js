import { extract, extractFromHtml } from '@extractus/article-extractor'
import { GoogleGenerativeAI, HarmCategory, HarmBlockThreshold } from '@google/generative-ai'
import { convert } from 'html-to-text'
import { StatusCodes } from 'http-status-codes'
import showdown from 'showdown'
import dedent from 'dedent'
import dotenv from 'dotenv'
import express from 'express'

dotenv.config()

const config = {
    port: process.env.PORT,
    gemini: {
        apiKey: process.env.GEMINI_API_KEY,
        model: {
            model: 'gemini-1.5-flash',
            safetySettings: [
                {category: HarmCategory.HARM_CATEGORY_HARASSMENT, threshold: HarmBlockThreshold.BLOCK_NONE},
                {category: HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold: HarmBlockThreshold.BLOCK_NONE},
                {category: HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold: HarmBlockThreshold.BLOCK_NONE},
                {category: HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold: HarmBlockThreshold.BLOCK_NONE}
            ],
        }
    },
    browser: {
        headers: {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.79 Safari/537.36'
        }
    }
}

const md2html = new showdown.Converter({tables: true, openLinksInNewWindow: true, completeHTMLDocument: true, metadata: true, moreStyling: true})
const llm = new GoogleGenerativeAI(config.gemini.apiKey).getGenerativeModel(config.gemini.model)

const askAi = (prompt) => llm.generateContent(dedent(prompt))
    .then(result => JSON.parse(result.response.text().replace('```json\n', '').replace('```', '')))

const summarize = (req, res) => {
    const url = req.query.url
    if (!url) return res.redirect('/')
    console.log(`Summarizing ${req.method} ${url} ...`)
    const parsed = req.body ? extractFromHtml(req.body, url) : extract(url, {}, config.browser)
    return parsed
        .then(res => Object.assign(res, {text: convert(res.content), originalUrl: url}))
        .then(parsed => askAi(`
            I have extracted the following information from this site:
            url: ${parsed.url},
            title: ${parsed.title},
            description ${parsed.description}
            content: ${parsed.text}

            Generate a short title and summarize the above content and respond using the following JSON schema:
            Return: {'title': string, 'summary': string}

            where:
            title: A short title for this content (max 3 or 4 words)

            summary: a short Markdown note with relevant sections, sub-sections - each with bulleted and numbered lists and sub-lists.
            The more structured the document is, the better.
            But, be sure to be very short and succint for each bulleted item.
            Feel free to include citations or links to products and resources as inline hyperlinks in Markdown.
            Also, feel free to tabulate in markdown if needed.
            Ignore disclaimers, self-promotions, acknowledgements etc.
        `))
        .then(({title, summary}) => `# [${title ?? parsed.title ?? parsed.description ?? parsed.url}](${parsed.originalUrl})\n\n${summary.replace(/\\n/g, '\n').replace(/\\t/g, '\t').replace(/\\"/g, '"')}`)
        .then(md => res.send(md2html.makeHtml(md)))
}

express()
    .get('/', (req, res) => res.send('URL Summarizer: Try /summarize?url=$url'))
    .get('/summarize', summarize)
    .post('/summarize', summarize)
    .use((err, req, res, next) => res.status(StatusCodes.INTERNAL_SERVER_ERROR).send(err.message))
    .listen(config.port, () => console.log(`Started server on port ${config.port} ...`))
