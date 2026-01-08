/**
 * Chat API Hook
 * Manages chat state and API interactions with the backend
 * Supports streaming responses via Server-Sent Events (SSE)
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { Message as LlamaMessage } from "@llamaindex/chat-ui";
import {
  type ChatMessage,
  createSessionApiChatSessionPost,
  getConversationHistoryApiChatHistorySessionIdGet,
} from "@/api-client";
import {
  createSseClient,
  type StreamEvent,
} from "@/api-client/core/serverSentEvents.gen";
import { client } from "@/lib/api-config";
import { sessionStorage } from "@/lib/session-storage";
import { useShowError } from "@/App";

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

// SSE event data types
interface TokenEvent {
  content: string;
}
interface StartEvent {
  session_id: string;
}
interface DoneEvent {
  content: string;
  session_id: string;
}
interface ErrorEvent {
  error: string;
  code: string;
  partial_content?: string;
}

type SseEventData = TokenEvent | StartEvent | DoneEvent | ErrorEvent;

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
 * Custom hook for chat API interactions with streaming support
 */
export function useChatApi(): UseChatApiResult {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const showError = useShowError();
  const abortControllerRef = useRef<AbortController | null>(null);

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
   * Send a message to the chat API with streaming response
   */
  const sendMessage = useCallback(
    async (content: string) => {
      if (!sessionId) {
        console.error("Send message called but no sessionId:", sessionId);
        return;
      }

      console.log("Sending message with session:", sessionId);

      // Cancel any ongoing request
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      abortControllerRef.current = new AbortController();
      abortControllerRef.current = new AbortController();

      setIsLoading(true);

      // Add user message immediately to UI
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: "user",
        parts: [{ type: "text", text: content }],
      };
      setMessages((prev) => [...prev, userMessage]);

      // Track assistant message state
      const assistantMessageId = `assistant-${Date.now()}`;
      let assistantMessageAdded = false;
      let accumulatedContent = "";

      // Helper to add or update assistant message
      const updateAssistantMessage = (text: string, error = false) => {
        if (!assistantMessageAdded) {
          setMessages((prev) => [
            ...prev,
            {
              id: assistantMessageId,
              role: "assistant",
              parts: [{ type: "text", text }],
              error,
            },
          ]);
          assistantMessageAdded = true;
        } else {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? { ...msg, parts: [{ type: "text", text }], error }
                : msg
            )
          );
        }
      };

      // Handle SSE events
      const handleSseEvent = (event: StreamEvent<unknown>) => {
        const { data, event: eventType } = event;
        const eventData = data as SseEventData;

        switch (eventType) {
          case "start":
            console.log(
              "Stream started:",
              (eventData as StartEvent).session_id,
            );
            break;

          case "token":
            accumulatedContent += (eventData as TokenEvent).content;
            updateAssistantMessage(accumulatedContent);
            break;

          case "done":
            console.log("Stream done");
            updateAssistantMessage((eventData as DoneEvent).content);
            break;

          case "error": {
            const { error, code, partial_content } = eventData as ErrorEvent;
            // Only show partial content in chat if any, error details go to toast
            if (partial_content) {
              updateAssistantMessage(partial_content, true);
            }
            showError(`Error: ${code}`, error);
            break;
          }
        }
      };

      try {
        const baseUrl = client.getConfig().baseUrl || "";

        const { stream } = createSseClient<SseEventData>({
          url: `${baseUrl}/api/chat/message`,
          method: "POST",
          headers: { "Content-Type": "application/json" },
          serializedBody: JSON.stringify({
            content,
            role: "user",
            session_id: sessionId,
          }),
          signal: abortControllerRef.current.signal,
          onSseEvent: handleSseEvent,
          onSseError: (error) => console.error("SSE error:", error),
          sseMaxRetryAttempts: 0,
        });

        // Consume the stream (events handled by onSseEvent)
        for await (const _ of stream) {
          // Events are processed in handleSseEvent callback
        }
      } catch (error) {
        if ((error as Error).name === "AbortError") {
          console.log("Request aborted");
          return;
        }

        console.error("Stream error:", error);
        const errorMessage = error instanceof Error
          ? error.message
          : "Unknown error";
        const errorText = accumulatedContent
          ? `${accumulatedContent}\n\n⚠️ Error: ${errorMessage}`
          : `⚠️ Error: ${errorMessage}`;
        updateAssistantMessage(errorText, true);
        showError("Failed to send message", errorMessage);
      } finally {
        setIsLoading(false);
        abortControllerRef.current = null;
      }
    },
    [sessionId, showError],
  );

  // Initialize session on mount
  useEffect(() => {
    initializeSession();
  }, [initializeSession]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  return {
    messages,
    isLoading,
    isInitializing,
    sessionId,
    sendMessage,
  };
}
