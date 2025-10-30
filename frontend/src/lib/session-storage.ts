/**
 * Session Storage Utility
 * Manages chat session ID persistence in browser storage
 */

const SESSION_KEY = "carlo_session_id";

/**
 * Check if localStorage is available
 */
function isLocalStorageAvailable(): boolean {
  try {
    // deno-lint-ignore no-window
    return typeof window !== "undefined" && window.localStorage !== null &&
      // deno-lint-ignore no-window
      window.localStorage !== undefined;
  } catch {
    return false;
  }
}

export const sessionStorage = {
  /**
   * Get the current session ID from storage
   */
  getSessionId(): string | null {
    try {
      if (!isLocalStorageAvailable()) {
        console.warn("localStorage is not available, session will not persist");
        return null;
      }
      return localStorage.getItem(SESSION_KEY);
    } catch (error) {
      console.error("Failed to get session ID:", error);
      return null;
    }
  },

  /**
   * Save session ID to storage
   */
  setSessionId(sessionId: string): void {
    try {
      if (!isLocalStorageAvailable()) {
        console.warn("localStorage is not available, session will not persist");
        return;
      }
      localStorage.setItem(SESSION_KEY, sessionId);
    } catch (error) {
      console.error("Failed to save session ID:", error);
    }
  },

  /**
   * Clear session ID from storage
   */
  clearSessionId(): void {
    try {
      if (!isLocalStorageAvailable()) {
        console.warn("localStorage is not available");
        return;
      }
      localStorage.removeItem(SESSION_KEY);
    } catch (error) {
      console.error("Failed to clear session ID:", error);
    }
  },
};
