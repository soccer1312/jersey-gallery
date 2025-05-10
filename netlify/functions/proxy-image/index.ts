import type { Handler } from "@netlify/functions"
import fetch from "node-fetch"

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

    // Make the request to the target URL with custom headers
    const response = await fetch(url, {
      headers: {
        "Referer": "https://www.yupoo.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
      }
    })
    const buffer = await response.buffer()
    const contentType = response.headers.get("content-type") || "image/jpeg"

    return {
      statusCode: 200,
      headers: {
        "Content-Type": contentType,
        "Cache-Control": "public, max-age=31536000"
      },
      body: buffer.toString("base64"),
      isBase64Encoded: true
    }
  } catch (error: any) {
    return {
      statusCode: 500,
      body: JSON.stringify({
        error: `An error occurred: ${error.message}`
      })
    }
  }
} 