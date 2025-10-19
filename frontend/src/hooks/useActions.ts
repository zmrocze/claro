/**
 * Actions Hook
 * Manages pending action confirmations and execution
 */

import { useCallback, useState } from "react";
import {
  type ActionConfirmation,
  type ActionResult,
  cancelActionApiActionsCancelActionIdDelete,
  confirmActionApiActionsConfirmActionIdPost,
  getPendingActionsApiActionsPendingGet,
} from "@/api-client";

interface UseActionsResult {
  pendingActions: ActionConfirmation[];
  isLoading: boolean;
  loadPendingActions: () => Promise<void>;
  confirmAction: (actionId: string) => Promise<ActionResult | null>;
  cancelAction: (actionId: string) => Promise<void>;
}

/**
 * Custom hook for action management
 */
export function useActions(): UseActionsResult {
  const [pendingActions, setPendingActions] = useState<ActionConfirmation[]>(
    [],
  );
  const [isLoading, setIsLoading] = useState(false);

  /**
   * Load pending actions from backend
   */
  const loadPendingActions = useCallback(async () => {
    setIsLoading(true);

    try {
      const response = await getPendingActionsApiActionsPendingGet();

      if (response.data) {
        setPendingActions(response.data);
      }
    } catch (err) {
      console.error("Failed to load pending actions:", err);
      // HTTP errors are shown by API interceptor
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Confirm and execute an action
   */
  const confirmAction = useCallback(
    async (actionId: string): Promise<ActionResult | null> => {
      setIsLoading(true);

      try {
        const response = await confirmActionApiActionsConfirmActionIdPost({
          path: { action_id: actionId },
        });

        if (response.data) {
          // Remove from pending actions
          setPendingActions((prev) =>
            prev.filter((action) => action.action_id !== actionId)
          );
          return response.data;
        }

        return null;
      } catch (err) {
        console.error("Failed to confirm action:", err);
        // HTTP errors are shown by API interceptor
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

  /**
   * Cancel a pending action
   */
  const cancelAction = useCallback(async (actionId: string) => {
    setIsLoading(true);

    try {
      await cancelActionApiActionsCancelActionIdDelete({
        path: { action_id: actionId },
      });

      // Remove from pending actions
      setPendingActions((prev) =>
        prev.filter((action) => action.action_id !== actionId)
      );
    } catch (err) {
      console.error("Failed to cancel action:", err);
      // HTTP errors are shown by API interceptor
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    pendingActions,
    isLoading,
    loadPendingActions,
    confirmAction,
    cancelAction,
  };
}
