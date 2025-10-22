/**
 * Chat API Hook
 * Manages chat state and API interactions with the backend
 */

import { useCallback, useEffect, useState } from "react";
import type { Message as LlamaMessage } from "@llamaindex/chat-ui";
import {
  type ChatMessage,
  createSessionApiChatSessionPost,
  getConversationHistoryApiChatHistorySessionIdGet,
  sendMessageApiChatMessagePost,
} from "@/api-client";
import { sessionStorage } from "@/lib/session-storage";
import { useShowError } from "@/App";

// Import API config to ensure client is configured
import "@/lib/api-config";

// Extended Message type with error state
export interface Message extends LlamaMessage {
  error?: boolean;
}

interface UseChatApiResult {
  messages: Message[];
  isLoading: boolean;
  isInitializing: boolean;
  sessionId: string | null;
  sendMessage: (content: string) => Promise<void>;
}

/**
 * Convert backend ChatMessage to llamaindex Message format
 */
function chatMessageToLlamaMessage(msg: ChatMessage, index: number): Message {
  return {
    id: `${msg.session_id || "unknown"}-${index}`,
    role: msg.role === "user" ? "user" : "assistant",
    parts: [{ type: "text", text: msg.content }],
  };
}

/**
 * Custom hook for chat API interactions
 */
export function useChatApi(): UseChatApiResult {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const showError = useShowError();

  /**
   * Load conversation history from backend
   */
  const loadHistory = useCallback(async (sessionId: string) => {
    try {
      const response = await getConversationHistoryApiChatHistorySessionIdGet({
        path: { session_id: sessionId },
        query: { limit: 50 },
      });

      if (response.data?.messages) {
        const llamaMessages = response.data.messages.map(
          (msg: ChatMessage, idx: number) =>
            chatMessageToLlamaMessage(msg, idx),
        );
        setMessages(llamaMessages);
      }
    } catch (err) {
      console.error("Failed to load history:", err);
      // HTTP errors shown by API interceptor. Continue with empty history - not critical.
    }
  }, []);

  /**
   * Initialize session - get existing or create new
   */
  const initializeSession = useCallback(async () => {
    setIsInitializing(true);

    try {
      // Try to get existing session
      let existingSessionId: string | null = sessionStorage.getSessionId();

      if (!existingSessionId) {
        // Create new session
        console.log("Creating new session...");
        const response = await createSessionApiChatSessionPost();
        console.log("Session creation response:", response);

        // Backend error already shown by interceptor
        if (response.error) {
          return;
        }

        // Validate response data
        if (response.data?.session_id) {
          existingSessionId = response.data.session_id;
          sessionStorage.setSessionId(existingSessionId as string);
          console.log("Session created:", existingSessionId);
        } else {
          // Backend returned success but invalid data - validation error
          showError(
            "Failed to initialize chat session",
            "Backend returned invalid session response (missing session_id)",
          );
          return;
        }
      } else {
        console.log("Using existing session:", existingSessionId);
      }

      setSessionId(existingSessionId);

      // Load conversation history if we have a session
      if (existingSessionId !== null) {
        await loadHistory(existingSessionId);
      }
    } finally {
      setIsInitializing(false);
    }
  }, [loadHistory, showError]);

  /**
   * Send a message to the chat API
   */
  const sendMessage = useCallback(
    async (content: string) => {
      if (!sessionId) {
        console.error("Send message called but no sessionId:", sessionId);
        // Error will be shown via global error handler
        return;
      }

      console.log("Sending message with session:", sessionId);

      setIsLoading(true);

      // Add user message immediately to UI
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: "user",
        parts: [{ type: "text", text: content }],
      };

      setMessages((prev) => [...prev, userMessage]);

      const markMessageAsError = () => {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === userMessage.id ? { ...msg, error: true } : msg
          )
        );
      };

      // Send message to backend
      const response = await sendMessageApiChatMessagePost({
        body: {
          content,
          role: "user",
          session_id: sessionId,
        },
      });

      // Check if we got an error (already shown by interceptor)
      if (response.error) {
        markMessageAsError();
        setIsLoading(false);
        return;
      }

      if (response.data) {
        const assistantResponse = response.data;

        // Add assistant response to UI
        const assistantMessage: Message = {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          parts: [{ type: "text", text: assistantResponse.content }],
        };

        setMessages((prev) => [...prev, assistantMessage]);

        // Handle action requests if needed
        if (
          assistantResponse.requires_action && assistantResponse.action_data
        ) {
          console.log("Action required:", assistantResponse.action_data);
          // TODO: Show action dialog (Phase 2)
        }
      } else {
        // Unexpected case: no data and no error
        showError("Failed to send message", "No response data from backend");
        markMessageAsError();
      }

      setIsLoading(false);
    },
    [sessionId, showError],
  );

  // Initialize session on mount
  useEffect(() => {
    initializeSession();
  }, [initializeSession]);

  return {
    messages,
    isLoading,
    isInitializing,
    sessionId,
    sendMessage,
  };
}
