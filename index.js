import { extract, extractFromHtml } from '@extractus/article-extractor'
import { GoogleGenerativeAI, HarmCategory, HarmBlockThreshold, FunctionDeclarationSchemaType } from '@google/generative-ai'
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
        apiVersion: "v1beta",
        model: {
            model: 'gemini-pro',
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
const genAi = new GoogleGenerativeAI(config.gemini.apiKey)

const summarize = (parsed) => {
    const fn = {
        name: "render_summary",
        description: "Display the summary of the content in markdown format",
        parameters: {
            type: FunctionDeclarationSchemaType.OBJECT,
            properties: {
                title: {
                    type: FunctionDeclarationSchemaType.STRING,
                    description: "A short title for this content (max 3 or 4 words)",
                },
                summary: {
                    type: FunctionDeclarationSchemaType.STRING,
                    description: "Summary of the content in markdown format",
                },
            },
            required: ["title", "summary"],
        }
    }
    const prompt = dedent(`
        I have extracted the following information from this site:
        url: ${parsed.url},
        title: ${parsed.title},
        description ${parsed.description}
        content: ${parsed.text}

        Please summarize above content into a short Markdown note with relevant sections, sub-sections - each with bulleted and numbered lists and sub-lists.
        The more structured the document is, the better.
        But, be sure to be very short and succint for each bulleted item.
        Feel free to include citations or links to products and resources as inline hyperlinks in Markdown.
        Also, feel free to tabulate in markdown if needed.
        Ignore disclaimers, self-promotions, acknowledgements etc.

        Please use the function call "${fn.name}" to display the summary of the content in markdown format.`
    )
    const model = config.gemini.model.model
    const llm = genAi.getGenerativeModel({model, tools: [{functionDeclarations: [fn]}]}, {apiVersion: config.gemini.apiVersion})
    return llm.generateContent(prompt)
        .then(result => result.response)
        .then(response => response.promptFeedback?.blockReason ? `## BLOCKED: \`${JSON.stringify(response.promptFeedback)}\`` : response.candidates[0]?.content?.parts[0]?.functionCall?.args)
        .then(({title, summary}) => `# [${title ?? parsed.title ?? parsed.description ?? parsed.url}](${parsed.originalUrl})\n\n${summary.replace(/\\n/g, '\n').replace(/\\t/g, '\t')}`)
}

const reqHandler = (req, res) => {
    const url = req.query.url
    if (!url) return res.redirect('/')
    console.log(`Summarizing ${req.method} ${url} ...`)
    const parsed = req.body ? extractFromHtml(req.body, url) : extract(url, {}, config.browser)
    return parsed
        .then(res => Object.assign(res, {text: convert(res.content), originalUrl: url}))
        .then(summarize)
        .then(md => res.send(md2html.makeHtml(md)))
        .catch(err => {
            console.error(err)
            return res.status(StatusCodes.INTERNAL_SERVER_ERROR).send(err.message)
        })
}

express()
    .get('/', (req, res) => res.send('URL Summarizer: Try /summarize?url=$url'))
    .get('/summarize', reqHandler)
    .post('/summarize', reqHandler)
    .listen(config.port, () => console.log(`Started server on port ${config.port} ...`))
