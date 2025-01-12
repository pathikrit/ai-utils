import OpenAI from 'openai'
import { zodResponseFormat } from 'openai/helpers/zod'
import { z } from 'zod'
import axios from 'axios'
import { StatusCodes } from 'http-status-codes'
import showdown from 'showdown'
import TurndownService from 'turndown'
import dedent from 'dedent'
import dotenv from 'dotenv'
import express from 'express'
import bodyParser from 'body-parser'
import * as fs from 'fs'

dotenv.config()

const config = {
    port: process.env.PORT,
    responseTtl: 60 * 60 * 1000,    // Store result cache for 1 hour
    openai: {
        apiKey: process.env.OPENAI_API_KEY,
        model: {
            version: 'gpt-4o',
        }
    },
    browser: {
        headers: {
            'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.5112.79 Safari/537.36'
        }
    }
}

const md2html = new showdown.Converter({tables: true, openLinksInNewWindow: true, completeHTMLDocument: true, metadata: true, moreStyling: true})
const html2md = new TurndownService()
const llm = new OpenAI()

const askAi = (prompt, name, schema) => llm.beta.chat.completions.parse({
    model: config.openai.model.version,
    messages: [{role: 'user', content: dedent(prompt)}],
    response_format: zodResponseFormat(schema, name),
}).then(result => result.choices[0].message.parsed)

const responseCache = new Map()
const immediateReturn = (handler) => (req, res) => {
    console.log(`${handler.name}: ${req.method} ${req.url} ...`)
    if (req.method === 'GET') return handler(req).then(fn => fn(res))
    const requestId = Date.now().toString() // TODO: use uuid
    responseCache.set(requestId, handler(req))
    setTimeout(() => responseCache.delete(requestId), config.responseTtl)
    return res.status(StatusCodes.ACCEPTED).send({id: requestId, resultUrl: `${req.protocol}://${req.get('host')}/result/${requestId}`})
}

const parseHtml = (req) => {
    console.log(`Parsing ${req.query.url} with body=${req.body?.substring(0, 10)} ...`)
    const body = req.body ? Promise.resolve(req.body) : axios.get(req.query.url, config.browser).then(res => res.data)
    return body.then(html => html2md.turndown(html))
}

const summarize = (req) => parseHtml(req)
    .then(markdown => askAi(`
        I have extracted the following information from this site:
        url: ${req.query.url},
        content: ${markdown}

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
    `,  'summary', z.object({title: z.string(), summary: z.string()})))
    .then(({title, summary}) => `# [${title ?? 'Original Article'}](${req.query.url})\n\n${summary.replace(/\\n/g, '\n').replace(/\\t/g, '\t').replace(/\\"/g, '"')}`)
    .then(md => res => res.send(md2html.makeHtml(md)))

const calendarize = (req) => parseHtml(req)
    .then(markdown => askAi(`
        I have extracted the following information from this site:
        url: ${req.query.url},
        content: ${markdown}

        Generate a calendar invite with given title, start date and time, end date and time, location and description and respond using the following JSON schema:
        Return: {'title': string, 'start': string, 'end': string, 'location': string, 'details': string}

        where:
        title: Event title
        start: Event start time in ISO format
        end: Event end time in ISO format
        location: Event location
        details: Event description (short)
    `, 'event', z.object({title: z.string(), start: z.string(), end: z.string(), location: z.string().optional(), details: z.string().optional()})))
    .then(arg => {
        const dateFormat = (d) => d.replaceAll('-', '').replaceAll(':', '').replaceAll('Z', '')
        arg.details = [arg.details, req.query.url].join('\n\n')
        arg.gcal = encodeURI(`https://calendar.google.com/calendar/render?action=TEMPLATE&text=${arg.title}&dates=${dateFormat(arg.start)}/${dateFormat(arg.end)}&location=${arg.location ?? ''}&details=${arg.details ?? ''}`)
        console.log(arg)
        return res => res.redirect(arg.gcal)
    })

const readme = md2html.makeHtml(fs.readFileSync('README.md').toString())
const parseHtmlBody = bodyParser.text({type: '*/*', limit: '50mb'})
express()
    .get('/', (req, res) => res.send(readme))
    .get('/result/:id', (req, res) => responseCache.has(req.params.id) ? responseCache.get(req.params.id).then(fn => fn(res)) : res.status(StatusCodes.NOT_FOUND).send(`Not Found requestId=${req.params.id}`))
    .get('/summarize', immediateReturn(summarize))
    .post('/summarize', parseHtmlBody, immediateReturn(summarize))
    .get('/calendarize', immediateReturn(calendarize))
    .post('/calendarize', parseHtmlBody, immediateReturn(calendarize))
    .use((err, req, res, next) => {
        console.error(err)
        res.status(StatusCodes.INTERNAL_SERVER_ERROR).send('ERROR: ' + err?.message ?? 'Internal Server Error')
    })
    .listen(config.port, () => console.log(`Started server on port ${config.port} ...`))
