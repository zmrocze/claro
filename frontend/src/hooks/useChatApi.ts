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
import { sessionStorage } from "@/lib/session-storage";
import { useShowError } from "@/App";

// Import API config to ensure client is configured
import "@/lib/api-config";

// API base URL for streaming endpoint
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ??
  "http://localhost:8000";

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
 * Parse SSE event from a line
 */
function parseSSELine(line: string): { event?: string; data?: string } {
  if (line.startsWith("event: ")) {
    return { event: line.slice(7) };
  }
  if (line.startsWith("data: ")) {
    return { data: line.slice(6) };
  }
  return {};
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

      setIsLoading(true);

      // Add user message immediately to UI
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: "user",
        parts: [{ type: "text", text: content }],
      };

      setMessages((prev) => [...prev, userMessage]);

      // Assistant message will be added when first token arrives
      const assistantMessageId = `assistant-${Date.now()}`;
      let assistantMessageAdded = false;
      let accumulatedContent = "";

      try {
        const response = await fetch(`${API_BASE_URL}/api/chat/message`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "text/event-stream",
          },
          body: JSON.stringify({
            content,
            role: "user",
            session_id: sessionId,
          }),
          signal: abortControllerRef.current.signal,
        });

        if (!response.ok) {
          throw new Error(`HTTP error: ${response.status}`);
        }

        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error("No response body");
        }

        const decoder = new TextDecoder();
        let buffer = "";
        let currentEvent = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || ""; // Keep incomplete line in buffer

          for (const line of lines) {
            const trimmedLine = line.trim();
            if (!trimmedLine) continue;

            const { event, data } = parseSSELine(trimmedLine);

            if (event) {
              currentEvent = event;
            } else if (data) {
              try {
                const parsed = JSON.parse(data);

                switch (currentEvent) {
                  case "start":
                    // Stream started, session_id confirmed
                    console.log("Stream started:", parsed.session_id);
                    break;

                  case "token":
                    // Add assistant message on first token if not added yet
                    if (!assistantMessageAdded) {
                      assistantMessageAdded = true;
                      setMessages((prev) => [
                        ...prev,
                        {
                          id: assistantMessageId,
                          role: "assistant",
                          parts: [{ type: "text", text: parsed.content }],
                        },
                      ]);
                      accumulatedContent = parsed.content;
                    } else {
                      // Append token to accumulated content
                      accumulatedContent += parsed.content;
                      setMessages((prev) =>
                        prev.map((msg) =>
                          msg.id === assistantMessageId
                            ? {
                              ...msg,
                              parts: [{
                                type: "text",
                                text: accumulatedContent,
                              }],
                            }
                            : msg
                        )
                      );
                    }
                    break;

                  case "done":
                    // Stream complete - ensure message exists
                    console.log("Stream done");
                    if (!assistantMessageAdded) {
                      // No tokens received, add the complete message
                      setMessages((prev) => [
                        ...prev,
                        {
                          id: assistantMessageId,
                          role: "assistant",
                          parts: [{ type: "text", text: parsed.content }],
                        },
                      ]);
                    } else {
                      setMessages((prev) =>
                        prev.map((msg) =>
                          msg.id === assistantMessageId
                            ? {
                              ...msg,
                              parts: [{ type: "text", text: parsed.content }],
                            }
                            : msg
                        )
                      );
                    }
                    break;

                  case "error": {
                    // Error occurred - show partial content + error
                    console.error("Stream error:", parsed);
                    const errorContent = parsed.partial_content
                      ? `${parsed.partial_content}\n\n⚠️ Error: ${parsed.error}`
                      : `⚠️ Error: ${parsed.error}`;
                    if (!assistantMessageAdded) {
                      setMessages((prev) => [
                        ...prev,
                        {
                          id: assistantMessageId,
                          role: "assistant",
                          parts: [{ type: "text", text: errorContent }],
                          error: true,
                        },
                      ]);
                    } else {
                      setMessages((prev) =>
                        prev.map((msg) =>
                          msg.id === assistantMessageId
                            ? {
                              ...msg,
                              parts: [{ type: "text", text: errorContent }],
                              error: true,
                            }
                            : msg
                        )
                      );
                    }
                    showError("Message failed", parsed.error);
                    break;
                  }
                }
              } catch (parseError) {
                console.error("Failed to parse SSE data:", data, parseError);
              }
            }
          }
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

        if (!assistantMessageAdded) {
          setMessages((prev) => [
            ...prev,
            {
              id: assistantMessageId,
              role: "assistant",
              parts: [{ type: "text", text: errorText }],
              error: true,
            },
          ]);
        } else {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessageId
                ? {
                  ...msg,
                  parts: [{ type: "text", text: errorText }],
                  error: true,
                }
                : msg
            )
          );
        }
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
