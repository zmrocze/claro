import { ChatSection as ChatSectionUI } from '@llamaindex/chat-ui'
import type { ChatHandler, Message } from '@llamaindex/chat-ui'

import '@llamaindex/chat-ui/styles/markdown.css'
import '@llamaindex/chat-ui/styles/pdf.css'
import '@llamaindex/chat-ui/styles/editor.css'
import { useChatApi } from '@/hooks/useChatApi'

/**
 * Main chat section component
 * Connects the llamaindex chat UI to our backend API
 */
export function ChatSection() {
  const { messages, isLoading, error, sendMessage, clearError } = useChatApi()

  // Create ChatHandler for llamaindex chat UI
  const handler: ChatHandler = {
    messages,
    status: isLoading ? 'streaming' : error ? 'error' : 'ready',
    sendMessage: async (message: Message) => {
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
    </div>
  )
}
