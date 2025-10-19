/**
 * Chat API Hook
 * Manages chat state and API interactions with the backend
 */

import { useCallback, useEffect, useState } from "react";
import type { Message } from "@llamaindex/chat-ui";
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

        if (response.data?.session_id) {
          existingSessionId = response.data.session_id;
          sessionStorage.setSessionId(existingSessionId as string);
          console.log("Session created:", existingSessionId);
        } else {
          // Frontend validation error - backend returned invalid response
          throw new Error(
            "Backend returned invalid session response (missing session_id)",
          );
        }
      } else {
        console.log("Using existing session:", existingSessionId);
      }

      setSessionId(existingSessionId);

      // Load conversation history if we have a session
      if (existingSessionId !== null) {
        await loadHistory(existingSessionId);
      }
    } catch (err) {
      console.error("Failed to initialize session:", err);
      // HTTP errors are already shown by API interceptor
      // Frontend validation errors need explicit toast
      if (err instanceof Error && !err.message.toLowerCase().includes("http")) {
        showError("Failed to initialize chat session", err.stack);
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

      try {
        // Send message to backend
        const response = await sendMessageApiChatMessagePost({
          body: {
            content,
            role: "user",
            session_id: sessionId,
          },
        });

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
          throw new Error("No response data from backend");
        }
      } catch (err) {
        console.error("Failed to send message:", err);

        // HTTP errors are already shown by API interceptor
        // Frontend validation errors need explicit toast
        if (
          err instanceof Error && !err.message.toLowerCase().includes("http")
        ) {
          showError("Failed to send message", err.stack);
        }

        // Remove the user message from UI on error
        setMessages((prev) => prev.slice(0, -1));
      } finally {
        setIsLoading(false);
      }
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
