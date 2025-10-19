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
      onClick={() => fullMessage && setIsExpanded(!isExpanded)}
    >
      <div className="flex items-start justify-between p-3">
        <div className="flex-1 pr-2">
          <p className="text-sm font-medium text-white">{message}</p>
          {isExpanded && fullMessage && (
            <pre className="mt-2 max-h-64 overflow-auto rounded bg-black/20 p-2 text-xs text-white">
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
          className="text-white/80 hover:text-white"
          aria-label="Close"
        >
          <X className="h-4 w-4" />
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
    <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col">
      {toasts.map((toast) => (
        <div key={toast.id} className="pointer-events-auto">
          <Toast {...toast} onClose={onClose} />
        </div>
      ))}
    </div>
  );
}
