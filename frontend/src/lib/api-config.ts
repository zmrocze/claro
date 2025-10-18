/**
 * API Client Configuration
 * Configures the @hey-api/client-fetch client with base URL and settings
 */

import { client } from '@/api-client'

// Configure the API client with base URL
client.setConfig({
  baseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
})

// Export the configured client for direct use if needed
export { client }
