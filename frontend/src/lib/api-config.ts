/**
 * API Client Configuration
 * Configures the @hey-api/client-fetch client with base URL and settings
 */

import { client } from "@/api-client/client.gen";

// Global error handler for API calls
let globalErrorHandler:
  | ((message: string, fullMessage?: string) => void)
  | null = null;

export function setGlobalErrorHandler(
  handler: (message: string, fullMessage?: string) => void,
) {
  globalErrorHandler = handler;
}

// Configure the API client with base URL
client.setConfig({
  baseUrl: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
});

// Add response interceptor to handle errors
client.interceptors.response.use(async (response) => {
  if (!response.ok && globalErrorHandler) {
    try {
      const contentType = response.headers.get("content-type");
      if (contentType?.includes("application/json")) {
        const errorData = await response.clone().json();

        // Handle structured AppError format
        if (errorData.description && errorData.name && errorData.source) {
          const message = `[${errorData.source}] ${errorData.description}`;
          const fullDetails = [
            `Error: ${errorData.name}`,
            `Source: ${errorData.source}`,
            `Description: ${errorData.description}`,
            errorData.caused_by ? `\nCaused by:\n${errorData.caused_by}` : "",
          ].filter(Boolean).join("\n");
          globalErrorHandler(message, fullDetails);
        } else {
          // Fallback for unstructured errors
          const message = errorData.detail || errorData.message ||
            `HTTP ${response.status}: ${response.statusText}`;
          const fullMessage = JSON.stringify(errorData, null, 2);
          globalErrorHandler(message, fullMessage);
        }
      } else {
        globalErrorHandler(`HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (_e) {
      // If we can't parse the error, just show the status
      globalErrorHandler(`HTTP ${response.status}: ${response.statusText}`);
    }
  }
  return response;
});

// Export the configured client for direct use if needed
export { client };
