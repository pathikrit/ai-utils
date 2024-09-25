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
const genAi = new GoogleGenerativeAI(config.gemini.apiKey)

const askAi = (prompt) => genAi.getGenerativeModel({model: config.gemini.model.model})
    .generateContent(prompt)
    .then(result => JSON.parse(result.response.text().replace('```json\n', '').replace('```', '')))

const summarize = (parsed) => {
    const prompt = dedent(`
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
    `)
    return askAi(prompt)
}

const reqHandler = (req, res) => {
    const url = req.query.url
    if (!url) return res.redirect('/')
    console.log(`Summarizing ${req.method} ${url} ...`)
    const parsed = req.body ? extractFromHtml(req.body, url) : extract(url, {}, config.browser)
    return parsed
        .then(res => Object.assign(res, {text: convert(res.content), originalUrl: url}))
        .then(summarize)
        .then(({title, summary}) => `# [${title ?? parsed.title ?? parsed.description ?? parsed.url}](${parsed.originalUrl})\n\n${summary.replace(/\\n/g, '\n').replace(/\\t/g, '\t').replace(/\\"/g, '"')}`)
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

// const urls = [
//     'https://www.whattoexpect.com/toddler/behavior/potty-training-problem-refusing-to-poop.aspx?xid=nl_parenting_20240211_34313723&utm_source=nl&utm_medium=email&utm_campaign=parenting&rbe=&utm_content=edit_20240211&document_id=281628&zdee=gAAAAABlfylsTCGMh4ZFNKAb15_gU-zgnnUKPVd5dQOEpJPQMtuKiZcPGYQqOhFQMD8Rquhq_2tHK7pPVSaQwlGkTumPBWJMk4FKjGm89Oz7yBJAj6EDdLI%3D',
//     'https://www.whattoexpect.com/toddler/sleep/toddler-safe-sleep-practices/?xid=nl_parenting_20240210_34308528&utm_source=nl&utm_medium=email&utm_campaign=parenting&rbe=&utm_content=st_top_20240210&document_id=312351&zdee=gAAAAABlfylsTCGMh4ZFNKAb15_gU-zgnnUKPVd5dQOEpJPQMtuKiZcPGYQqOhFQMD8Rquhq_2tHK7pPVSaQwlGkTumPBWJMk4FKjGm89Oz7yBJAj6EDdLI%3D',
//     'https://www.whattoexpect.com/baby-products/sleep/best-toddler-pillow?xid=nl_parenting_20240210_34308528&utm_source=nl&utm_medium=email&utm_campaign=parenting&rbe=&utm_content=edit_20240210&document_id=330119&zdee=gAAAAABlfylsTCGMh4ZFNKAb15_gU-zgnnUKPVd5dQOEpJPQMtuKiZcPGYQqOhFQMD8Rquhq_2tHK7pPVSaQwlGkTumPBWJMk4FKjGm89Oz7yBJAj6EDdLI%3D',
//     'https://www.whattoexpect.com/community/parenting-trends-youll-see-in-2024?xid=nl_parenting_20240209_34299623&utm_source=nl&utm_medium=email&utm_campaign=parenting&rbe=&utm_content=edit_20240209&document_id=330808&zdee=gAAAAABlfylsTCGMh4ZFNKAb15_gU-zgnnUKPVd5dQOEpJPQMtuKiZcPGYQqOhFQMD8Rquhq_2tHK7pPVSaQwlGkTumPBWJMk4FKjGm89Oz7yBJAj6EDdLI%3D',
//     'https://www.whattoexpect.com/toddler/behavior/masturbating.aspx?xid=nl_parenting_20240209_34299623&utm_source=nl&utm_medium=email&utm_campaign=parenting&rbe=&utm_content=st_top_20240209&document_id=281626&zdee=gAAAAABlfylsTCGMh4ZFNKAb15_gU-zgnnUKPVd5dQOEpJPQMtuKiZcPGYQqOhFQMD8Rquhq_2tHK7pPVSaQwlGkTumPBWJMk4FKjGm89Oz7yBJAj6EDdLI%3D',
//     'https://www.whattoexpect.com/baby-growth/predict-height.aspx?xid=nl_parenting_20240208_34284838&utm_source=nl&utm_medium=email&utm_campaign=parenting&rbe=&utm_content=st_top_20240208&document_id=284590&zdee=gAAAAABlfylsTCGMh4ZFNKAb15_gU-zgnnUKPVd5dQOEpJPQMtuKiZcPGYQqOhFQMD8Rquhq_2tHK7pPVSaQwlGkTumPBWJMk4FKjGm89Oz7yBJAj6EDdLI%3D',
//     'https://www.whattoexpect.com/toddler/behavior/night-waking.aspx?xid=nl_parenting_20240207_34270933&utm_source=nl&utm_medium=email&utm_campaign=parenting&rbe=&utm_content=st_top_20240207&document_id=281553&zdee=gAAAAABlfylsTCGMh4ZFNKAb15_gU-zgnnUKPVd5dQOEpJPQMtuKiZcPGYQqOhFQMD8Rquhq_2tHK7pPVSaQwlGkTumPBWJMk4FKjGm89Oz7yBJAj6EDdLI%3D',
//     'https://www.whattoexpect.com/baby-products/nursery/best-baby-books-newborns-one-year-olds/?xid=nl_parenting_20240204_34232521&utm_source=nl&utm_medium=email&utm_campaign=parenting&rbe=&utm_content=edit_20240204&document_id=328477&zdee=gAAAAABlfylsTCGMh4ZFNKAb15_gU-zgnnUKPVd5dQOEpJPQMtuKiZcPGYQqOhFQMD8Rquhq_2tHK7pPVSaQwlGkTumPBWJMk4FKjGm89Oz7yBJAj6EDdLI%3D',
//     'https://www.whattoexpect.com/toddler/behavior/undressing.aspx?xid=nl_parenting_20240205_34243271&utm_source=nl&utm_medium=email&utm_campaign=parenting&rbe=&utm_content=edit_20240205&document_id=284458&zdee=gAAAAABlfylsTCGMh4ZFNKAb15_gU-zgnnUKPVd5dQOEpJPQMtuKiZcPGYQqOhFQMD8Rquhq_2tHK7pPVSaQwlGkTumPBWJMk4FKjGm89Oz7yBJAj6EDdLI%3D',
//     'https://www.whattoexpect.com/nursery-decorating/childproofing-basics.aspx?xid=nl_parenting_20231218_33735461&utm_source=nl&utm_medium=email&utm_campaign=parenting&rbe=&utm_content=edit_20231218&document_id=281608&zdee=gAAAAABlfylsTCGMh4ZFNKAb15_gU-zgnnUKPVd5dQOEpJPQMtuKiZcPGYQqOhFQMD8Rquhq_2tHK7pPVSaQwlGkTumPBWJMk4FKjGm89Oz7yBJAj6EDdLI%3D',
// ]

// const url2Text = (url) => extract(url, {}, config.browser).then(res => Object.assign(res, {text: convert(res.content), originalUrl: url}))
// const res =  await url2Text(urls[0]).then(summarize)
// console.log(JSON.stringify(res))