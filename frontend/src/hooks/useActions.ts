/**
 * Actions Hook
 * Manages pending action confirmations and execution
 */

import { useState, useCallback } from 'react'
import {
  getPendingActionsApiActionsPendingGet,
  confirmActionApiActionsConfirmActionIdPost,
  cancelActionApiActionsCancelActionIdDelete,
  type ActionConfirmation,
  type ActionResult,
} from '@/api-client'

interface UseActionsResult {
  pendingActions: ActionConfirmation[]
  isLoading: boolean
  error: string | null
  loadPendingActions: () => Promise<void>
  confirmAction: (actionId: string) => Promise<ActionResult | null>
  cancelAction: (actionId: string) => Promise<void>
  clearError: () => void
}

/**
 * Custom hook for action management
 */
export function useActions(): UseActionsResult {
  const [pendingActions, setPendingActions] = useState<ActionConfirmation[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  /**
   * Load pending actions from backend
   */
  const loadPendingActions = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await getPendingActionsApiActionsPendingGet()

      if (response.data) {
        setPendingActions(response.data)
      }
    } catch (err) {
      console.error('Failed to load pending actions:', err)
      setError('Failed to load pending actions')
    } finally {
      setIsLoading(false)
    }
  }, [])

  /**
   * Confirm and execute an action
   */
  const confirmAction = useCallback(
    async (actionId: string): Promise<ActionResult | null> => {
      setIsLoading(true)
      setError(null)

      try {
        const response = await confirmActionApiActionsConfirmActionIdPost({
          path: { action_id: actionId },
        })

        if (response.data) {
          // Remove from pending actions
          setPendingActions(prev =>
            prev.filter(action => action.action_id !== actionId)
          )
          return response.data
        }

        return null
      } catch (err) {
        console.error('Failed to confirm action:', err)
        setError('Failed to confirm action')
        return null
      } finally {
        setIsLoading(false)
      }
    },
    []
  )

  /**
   * Cancel a pending action
   */
  const cancelAction = useCallback(async (actionId: string) => {
    setIsLoading(true)
    setError(null)

    try {
      await cancelActionApiActionsCancelActionIdDelete({
        path: { action_id: actionId },
      })

      // Remove from pending actions
      setPendingActions(prev =>
        prev.filter(action => action.action_id !== actionId)
      )
    } catch (err) {
      console.error('Failed to cancel action:', err)
      setError('Failed to cancel action')
    } finally {
      setIsLoading(false)
    }
  }, [])

  /**
   * Clear error state
   */
  const clearError = useCallback(() => {
    setError(null)
  }, [])

  return {
    pendingActions,
    isLoading,
    error,
    loadPendingActions,
    confirmAction,
    cancelAction,
    clearError,
  }
}
