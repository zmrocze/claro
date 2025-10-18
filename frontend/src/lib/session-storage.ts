/**
 * Session Storage Utility
 * Manages chat session ID persistence in browser storage
 */

const SESSION_KEY = 'carlo_session_id'

export const sessionStorage = {
  /**
   * Get the current session ID from storage
   */
  getSessionId(): string | null {
    try {
      return localStorage.getItem(SESSION_KEY)
    } catch (error) {
      console.error('Failed to get session ID:', error)
      return null
    }
  },

  /**
   * Save session ID to storage
   */
  setSessionId(sessionId: string): void {
    try {
      localStorage.setItem(SESSION_KEY, sessionId)
    } catch (error) {
      console.error('Failed to save session ID:', error)
    }
  },

  /**
   * Clear session ID from storage
   */
  clearSessionId(): void {
    try {
      localStorage.removeItem(SESSION_KEY)
    } catch (error) {
      console.error('Failed to clear session ID:', error)
    }
  },
}
