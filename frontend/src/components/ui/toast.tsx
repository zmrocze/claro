/**
 * Toast notification component for displaying errors and messages
 */

import * as React from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface ToastProps {
  id: string;
  message: string;
  fullMessage?: string;
  onClose: (id: string) => void;
}

export function Toast({ id, message, fullMessage, onClose }: ToastProps) {
  const [isExpanded, setIsExpanded] = React.useState(false);

  return (
    <div
      className={cn(
        "mb-2 flex cursor-pointer flex-col rounded-lg bg-red-500 shadow-lg transition-all hover:bg-red-600",
        isExpanded ? "w-96" : "w-80",
      )}
      style={{
        pointerEvents: "auto",
        marginBottom: "0.5rem",
        // Add explicit inline styles to ensure visibility
        backgroundColor: "#ef4444",
        color: "white",
        padding: "0.75rem",
        borderRadius: "0.5rem",
        width: isExpanded ? "24rem" : "20rem",
        boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.1)",
        cursor: "pointer",
        display: "flex",
        flexDirection: "column",
      }}
      onClick={() => fullMessage && setIsExpanded(!isExpanded)}
    >
      <div
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
        }}
      >
        <div style={{ flex: 1, paddingRight: "0.5rem" }}>
          <p
            style={{
              fontSize: "0.875rem",
              fontWeight: 500,
              color: "white",
              margin: 0,
            }}
          >
            {message}
          </p>
          {isExpanded && fullMessage && (
            <pre
              style={{
                marginTop: "0.5rem",
                maxHeight: "16rem",
                overflow: "auto",
                borderRadius: "0.25rem",
                backgroundColor: "rgba(0, 0, 0, 0.2)",
                padding: "0.5rem",
                fontSize: "0.75rem",
                color: "white",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {fullMessage}
            </pre>
          )}
        </div>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onClose(id);
          }}
          style={{
            color: "rgba(255, 255, 255, 0.8)",
            background: "none",
            border: "none",
            cursor: "pointer",
            padding: 0,
          }}
          aria-label="Close"
        >
          <X style={{ width: "1rem", height: "1rem" }} />
        </button>
      </div>
    </div>
  );
}

interface ToastContainerProps {
  toasts: Array<{
    id: string;
    message: string;
    fullMessage?: string;
  }>;
  onClose: (id: string) => void;
}

export function ToastContainer({ toasts, onClose }: ToastContainerProps) {
  return (
    <div
      className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col"
      style={{
        position: "fixed",
        bottom: "1rem",
        right: "1rem",
        zIndex: 9999,
        pointerEvents: "none",
      }}
    >
      {toasts.map((toast) => (
        <Toast key={toast.id} {...toast} onClose={onClose} />
      ))}
    </div>
  );
}
