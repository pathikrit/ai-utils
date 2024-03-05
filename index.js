import { extract } from '@extractus/article-extractor'
import { GoogleGenerativeAI } from '@google/generative-ai'
import { convert } from 'html-to-text'
import dedent from 'dedent'

const urls = [
  'https://www.whattoexpect.com/toddler/behavior/potty-training-problem-refusing-to-poop.aspx?xid=nl_parenting_20240211_34313723&utm_source=nl&utm_medium=email&utm_campaign=parenting&rbe=&utm_content=edit_20240211&document_id=281628&zdee=gAAAAABlfylsTCGMh4ZFNKAb15_gU-zgnnUKPVd5dQOEpJPQMtuKiZcPGYQqOhFQMD8Rquhq_2tHK7pPVSaQwlGkTumPBWJMk4FKjGm89Oz7yBJAj6EDdLI%3D',
  'https://www.whattoexpect.com/toddler/sleep/toddler-safe-sleep-practices/?xid=nl_parenting_20240210_34308528&utm_source=nl&utm_medium=email&utm_campaign=parenting&rbe=&utm_content=st_top_20240210&document_id=312351&zdee=gAAAAABlfylsTCGMh4ZFNKAb15_gU-zgnnUKPVd5dQOEpJPQMtuKiZcPGYQqOhFQMD8Rquhq_2tHK7pPVSaQwlGkTumPBWJMk4FKjGm89Oz7yBJAj6EDdLI%3D',
  'https://www.whattoexpect.com/baby-products/sleep/best-toddler-pillow?xid=nl_parenting_20240210_34308528&utm_source=nl&utm_medium=email&utm_campaign=parenting&rbe=&utm_content=edit_20240210&document_id=330119&zdee=gAAAAABlfylsTCGMh4ZFNKAb15_gU-zgnnUKPVd5dQOEpJPQMtuKiZcPGYQqOhFQMD8Rquhq_2tHK7pPVSaQwlGkTumPBWJMk4FKjGm89Oz7yBJAj6EDdLI%3D',
  'https://www.whattoexpect.com/community/parenting-trends-youll-see-in-2024?xid=nl_parenting_20240209_34299623&utm_source=nl&utm_medium=email&utm_campaign=parenting&rbe=&utm_content=edit_20240209&document_id=330808&zdee=gAAAAABlfylsTCGMh4ZFNKAb15_gU-zgnnUKPVd5dQOEpJPQMtuKiZcPGYQqOhFQMD8Rquhq_2tHK7pPVSaQwlGkTumPBWJMk4FKjGm89Oz7yBJAj6EDdLI%3D',
  'https://www.whattoexpect.com/toddler/behavior/masturbating.aspx?xid=nl_parenting_20240209_34299623&utm_source=nl&utm_medium=email&utm_campaign=parenting&rbe=&utm_content=st_top_20240209&document_id=281626&zdee=gAAAAABlfylsTCGMh4ZFNKAb15_gU-zgnnUKPVd5dQOEpJPQMtuKiZcPGYQqOhFQMD8Rquhq_2tHK7pPVSaQwlGkTumPBWJMk4FKjGm89Oz7yBJAj6EDdLI%3D',
  'https://www.whattoexpect.com/baby-growth/predict-height.aspx?xid=nl_parenting_20240208_34284838&utm_source=nl&utm_medium=email&utm_campaign=parenting&rbe=&utm_content=st_top_20240208&document_id=284590&zdee=gAAAAABlfylsTCGMh4ZFNKAb15_gU-zgnnUKPVd5dQOEpJPQMtuKiZcPGYQqOhFQMD8Rquhq_2tHK7pPVSaQwlGkTumPBWJMk4FKjGm89Oz7yBJAj6EDdLI%3D',
  'https://www.whattoexpect.com/toddler/behavior/night-waking.aspx?xid=nl_parenting_20240207_34270933&utm_source=nl&utm_medium=email&utm_campaign=parenting&rbe=&utm_content=st_top_20240207&document_id=281553&zdee=gAAAAABlfylsTCGMh4ZFNKAb15_gU-zgnnUKPVd5dQOEpJPQMtuKiZcPGYQqOhFQMD8Rquhq_2tHK7pPVSaQwlGkTumPBWJMk4FKjGm89Oz7yBJAj6EDdLI%3D',
  'https://www.whattoexpect.com/baby-products/nursery/best-baby-books-newborns-one-year-olds/?xid=nl_parenting_20240204_34232521&utm_source=nl&utm_medium=email&utm_campaign=parenting&rbe=&utm_content=edit_20240204&document_id=328477&zdee=gAAAAABlfylsTCGMh4ZFNKAb15_gU-zgnnUKPVd5dQOEpJPQMtuKiZcPGYQqOhFQMD8Rquhq_2tHK7pPVSaQwlGkTumPBWJMk4FKjGm89Oz7yBJAj6EDdLI%3D',
  'https://www.whattoexpect.com/toddler/behavior/undressing.aspx?xid=nl_parenting_20240205_34243271&utm_source=nl&utm_medium=email&utm_campaign=parenting&rbe=&utm_content=edit_20240205&document_id=284458&zdee=gAAAAABlfylsTCGMh4ZFNKAb15_gU-zgnnUKPVd5dQOEpJPQMtuKiZcPGYQqOhFQMD8Rquhq_2tHK7pPVSaQwlGkTumPBWJMk4FKjGm89Oz7yBJAj6EDdLI%3D',
  'https://www.whattoexpect.com/nursery-decorating/childproofing-basics.aspx?xid=nl_parenting_20231218_33735461&utm_source=nl&utm_medium=email&utm_campaign=parenting&rbe=&utm_content=edit_20231218&document_id=281608&zdee=gAAAAABlfylsTCGMh4ZFNKAb15_gU-zgnnUKPVd5dQOEpJPQMtuKiZcPGYQqOhFQMD8Rquhq_2tHK7pPVSaQwlGkTumPBWJMk4FKjGm89Oz7yBJAj6EDdLI%3D',
]
process.env.NODE_TLS_REJECT_UNAUTHORIZED = "0"

const urlToText = (url) => extract(url).then(res => Object.assign(res, {text: convert(res.content)}))

const makePrompt = async (urlParse, current) => {
    const urlPrompt = dedent(`
        I have extracted the following information from this site:
        url: ${urlParse.url},
        title: ${urlParse.title},
        description ${urlParse.description}
        content: ${urlParse.text}
    `)

    const stylePrompt = dedent(`
    short Markdown document with relevant sections, sub-sections with bulleted lists and sub-lists.
    Be very short and succint for each bullet items. Discard useless disclaimers and boilerplate cruft from the article.
    `)
    
    if (current) {
        return dedent(`
        I have the following Markdown document of my notes:

        ${current}

        Also, ${urlPrompt}

        Please incorporate information from the above site into my original Markdown notes (remove or combine duplicate information as needed).
        Keep the the original writing style of ${stylePrompt}. Feel free to create any new thematics sections or add a new sub-section if needed.
        Remove any empty section or sub-section.
        `)
    } else {
        return dedent(`
        ${urlPrompt}

        Please summarize above content into a ${stylePrompt}.
        `)
    }
}

class Gemini {
    static API_KEY = 'AIzaSyBx0jD3n1_mhi1oKJCgn_JjbNhLjaDKhT0'
    static MODEL = 'gemini-pro'
    static llm = new GoogleGenerativeAI(Gemini.API_KEY).getGenerativeModel({model: Gemini.MODEL})
    static ask = (prompt) => Gemini.llm.generateContent(prompt).then(result => result.response)
}

let doc = null
for (const url of urls) {
    console.log(`Reading ${url} ...`)
    doc = await urlToText(url)
        .then(urlParse => makePrompt(urlParse, doc))
        .then(prompt => Gemini.ask(prompt))
        .then(response => response.text())
    console.log(doc)
    console.log('XXXXXXXXXXXXXXXXXXXXXXXXX')
}

console.log(doc)
// TODO: 
// 1. streaming
// 2. citations https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/gemini#response_body
// 3. stream logs