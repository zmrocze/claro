import { ChatSection as ChatSectionUI } from '@llamaindex/chat-ui'
import type { ChatHandler, Message } from '@llamaindex/chat-ui'

import '@llamaindex/chat-ui/styles/markdown.css'
import '@llamaindex/chat-ui/styles/pdf.css'
import '@llamaindex/chat-ui/styles/editor.css'
import { useChatApi } from '@/hooks/useChatApi'
import { useActions } from '@/hooks/useActions'
import { ActionDialog } from './action-dialog'
import { useState, useEffect } from 'react'

/**
 * Main chat section component
 * Connects the llamaindex chat UI to our backend API
 */
export function ChatSection() {
  const { messages, isLoading, isInitializing, error, sendMessage, clearError } =
    useChatApi()
  const {
    pendingActions,
    isLoading: actionsLoading,
    confirmAction,
    cancelAction,
    loadPendingActions,
  } = useActions()

  const [currentAction, setCurrentAction] = useState<typeof pendingActions[0] | null>(null)
  const [showActionDialog, setShowActionDialog] = useState(false)

  // Check for pending actions when component mounts or messages change
  useEffect(() => {
    const checkPendingActions = async () => {
      await loadPendingActions()
    }

    // Check after each message exchange
    if (messages.length > 0 && !isLoading) {
      checkPendingActions()
    }
  }, [messages.length, isLoading, loadPendingActions])

  // Show dialog for first pending action
  useEffect(() => {
    if (pendingActions.length > 0 && !showActionDialog) {
      setCurrentAction(pendingActions[0])
      setShowActionDialog(true)
    }
  }, [pendingActions, showActionDialog])

  // Handle action confirmation
  const handleConfirmAction = async () => {
    if (!currentAction) return

    const result = await confirmAction(currentAction.action_id)

    if (result) {
      console.log('Action executed:', result)
      // Could show a success message here
    }

    setShowActionDialog(false)
    setCurrentAction(null)

    // Check for more pending actions
    await loadPendingActions()
  }

  // Handle action cancellation
  const handleCancelAction = async () => {
    if (!currentAction) return

    await cancelAction(currentAction.action_id)
    setShowActionDialog(false)
    setCurrentAction(null)

    // Check for more pending actions
    await loadPendingActions()
  }

  // Create ChatHandler for llamaindex chat UI
  const handler: ChatHandler = {
    messages,
    status: isInitializing
      ? 'ready'
      : isLoading
        ? 'streaming'
        : error
          ? 'error'
          : 'ready',
    sendMessage: async (message: Message) => {
      // Don't allow sending if still initializing
      if (isInitializing) {
        console.warn('Cannot send message while initializing')
        return
      }

      // Extract text content from message parts
      const textContent = message.parts
        .filter(part => part.type === 'text')
        .map(part => ('text' in part ? part.text : ''))
        .join(' ')

      if (textContent.trim()) {
        await sendMessage(textContent)
      }
    },
  }

  return (
    <div className="flex h-full max-h-[85vh] flex-col gap-6">
      {isInitializing && (
        <div className="rounded-lg border border-blue-300 bg-blue-50 p-4 text-blue-800">
          <p className="text-sm">Initializing chat session...</p>
        </div>
      )}
      {error && (
        <div className="rounded-lg border border-red-300 bg-red-50 p-4 text-red-800">
          <div className="flex items-center justify-between">
            <p className="text-sm">{error}</p>
            <button
              onClick={clearError}
              className="text-red-600 hover:text-red-800"
            >
              ✕
            </button>
          </div>
        </div>
      )}
      <div className="flex flex-1 flex-col overflow-y-auto">
        <ChatSectionUI handler={handler} />
      </div>

      {/* Action Confirmation Dialog */}
      <ActionDialog
        action={currentAction}
        open={showActionDialog}
        onConfirm={handleConfirmAction}
        onCancel={handleCancelAction}
        isLoading={actionsLoading}
      />
    </div>
  )
}
