import { extract } from '@extractus/article-extractor'
import { GoogleGenerativeAI, HarmCategory, HarmBlockThreshold } from '@google/generative-ai'
import { convert } from 'html-to-text'
import showdown from 'showdown'
import dedent from 'dedent'
import fs from 'node:fs/promises'
import express from 'express'

process.env.NODE_TLS_REJECT_UNAUTHORIZED = 0

const config = {
    port: 3000,
    gemini: {
        apiKey: 'AIzaSyBx0jD3n1_mhi1oKJCgn_JjbNhLjaDKhT0',
        model: {
            model: 'gemini-pro',
            safetySettings: [
                {category: HarmCategory.HARM_CATEGORY_HARASSMENT, threshold: HarmBlockThreshold.BLOCK_NONE},
                {category: HarmCategory.HARM_CATEGORY_HATE_SPEECH, threshold: HarmBlockThreshold.BLOCK_NONE},
                {category: HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold: HarmBlockThreshold.BLOCK_NONE},
                {category: HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold: HarmBlockThreshold.BLOCK_NONE}
            ]
        }
    }
}

const md2html = new showdown.Converter({tables: true, openLinksInNewWindow: true, completeHTMLDocument: true, metadata: true, moreStyling: true})

const llm = new GoogleGenerativeAI(config.gemini.apiKey).getGenerativeModel(config.gemini.model)

const parseUrl = (url) => extract(url).then(res => Object.assign(res, {text: convert(res.content), originalUrl: url}))

const summarize = (parsed) => {
    const prompt = dedent(`
        I have extracted the following information from this site:
        url: ${parsed.url},
        title: ${parsed.title},
        description ${parsed.description}
        content: ${parsed.text}

        Please summarize above content into a short Markdown document with relevant sections, sub-sections with bulleted and numbered lists and sub-lists.
        Be very short and succint
        Ignore disclaimers, self-propotions, acknowledgements etc.
        Feel free to include citations or links to products as inline hyperlinks in Markdown
    `)
    return llm.generateContent(prompt)
        .then(result => result.response)
        .then(response => response.promptFeedback?.blockReason ? `## BLOCKED: \`${JSON.stringify(response.promptFeedback)}\`` : response.text())
        .then(doc => `# [${parsed.title ?? parsed.description ?? parsed.url}](${parsed.originalUrl})\n\n${doc}`)
}

express()
    .get('/', (req, res) => res.send('URL Summarizer: Try /summarize?url=$url'))
    .get('/summarize', (req, res) => {
        const url = req.query.url
        if (!url) return res.redirect('/')
        console.log(`Summarizing ${url} ...`)
        return parseUrl(url)
            .then(summarize)
            .then(md => res.send(md2html.makeHtml(md)))
            .catch(err => {
                console.error(err)
                res.status(500).send(err)
            })
    })
    .listen(config.port, () => console.log(`Started server on port ${config.port} ...`))


// TODO
// 1. status codes
// 2. blocks
// 3. .env