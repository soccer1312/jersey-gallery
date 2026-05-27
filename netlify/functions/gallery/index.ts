import type { Handler } from "@netlify/functions"
import * as fs from "fs"
import * as path from "path"

interface Jersey {
  title: string
  url: string
  images: string[]
  thumbnail: string
  description: string
  page: number
}

interface JerseyResponse {
  total: number
  total_pages: number
  last_page: number
  jerseys: Jersey[]
}

export const handler: Handler = async (event, context) => {
  try {
    // Log the current directory and available files
    const currentDir = process.cwd()
    console.log("Current directory:", currentDir)

    // Try to read the jerseys.json file
    const jsonPath = path.join(currentDir, "netlify", "functions", "shared", "jerseys.json")
    console.log("Attempting to read file at:", jsonPath)

    if (!fs.existsSync(jsonPath)) {
      console.error("jerseys.json file not found at:", jsonPath)
      return {
        statusCode: 404,
        body: JSON.stringify({
          error: "Jerseys data file not found"
        })
      }
    }

    // Get query parameters for filtering
    const { page, search } = event.queryStringParameters || {}
    console.log("Query parameters:", { page, search })

    // Read and parse the JSON file
    const jsonData = fs.readFileSync(jsonPath, "utf-8")
    const data: JerseyResponse = JSON.parse(jsonData)
    console.log("Successfully parsed JSON data")

    // Filter jerseys based on search parameter
    let filteredJerseys = data.jerseys
    if (search) {
      const searchLower = search.toLowerCase()
      filteredJerseys = filteredJerseys.filter(jersey => 
        jersey.title.toLowerCase().includes(searchLower) ||
        jersey.description.toLowerCase().includes(searchLower)
      )
    }

    // Handle pagination
    const pageNumber = page ? parseInt(page) : 1
    const itemsPerPage = 80
    const startIndex = (pageNumber - 1) * itemsPerPage
    const endIndex = startIndex + itemsPerPage
    const paginatedJerseys = filteredJerseys.slice(startIndex, endIndex)

    // Calculate pagination info
    const totalItems = filteredJerseys.length
    const totalPages = Math.ceil(totalItems / itemsPerPage)

    console.log(`Returning ${paginatedJerseys.length} jerseys for page ${pageNumber}`)

    return {
      statusCode: 200,
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "public, max-age=3600" // Cache for 1 hour
      },
      body: JSON.stringify({
        total: totalItems,
        total_pages: totalPages,
        current_page: pageNumber,
        jerseys: paginatedJerseys
      })
    }
  } catch (error: any) {
    console.error("Error in gallery function:", error)
    return {
      statusCode: 500,
      body: JSON.stringify({
        error: `Failed to load gallery: ${error.message}`,
        stack: error.stack
      })
    }
  }
} 