import type { Handler } from "@netlify/functions"
import fetch from "node-fetch"
import * as cheerio from "cheerio"

export const handler: Handler = async (event, context) => {
  try {
    // Get the URL from the query parameters
    const url = event.queryStringParameters?.url

    if (!url) {
      return {
        statusCode: 400,
        body: JSON.stringify({
          error: "URL parameter is required"
        })
      }
    }

    // Make the request to the target URL
    const response = await fetch(url)
    const html = await response.text()

    // Parse the HTML content
    const $ = cheerio.load(html)

    // Extract the title
    const title = $("title").text() || ""

    // Extract meta description
    const description = $('meta[name="description"]').attr("content") || ""

    // Extract main content
    const content = $("main").text() || $("article").text() || $(".content").text() || ""

    return {
      statusCode: 200,
      body: JSON.stringify({
        title,
        description,
        content
      })
    }
  } catch (error) {
    return {
      statusCode: 500,
      body: JSON.stringify({
        error: `An error occurred: ${error.message}`
      })
    }
  }
} 