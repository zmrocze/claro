import "./App.css";
import { ChatSection } from "./components/chat";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { ToastContainer } from "./components/ui/toast";
import { setGlobalErrorHandler } from "./lib/api-config";

interface Toast {
  id: string;
  message: string;
  fullMessage?: string;
}

interface ErrorContextType {
  showError: (message: string, fullMessage?: string) => void;
}

const ErrorContext = createContext<ErrorContextType | null>(null);

// Export hook for other components to use
export function useShowError() {
  const context = useContext(ErrorContext);
  if (!context) {
    throw new Error("useShowError must be used within App");
  }
  return context.showError;
}

function App() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showError = useCallback((message: string, fullMessage?: string) => {
    const id = `${Date.now()}-${Math.random()}`;
    const toast: Toast = { id, message, fullMessage };

    setToasts((prev) => [...prev, toast]);

    // Auto-dismiss after 10 seconds
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 10000);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // Initialize global API error handler
  useEffect(() => {
    setGlobalErrorHandler(showError);
    return () => {
      setGlobalErrorHandler(() => {});
    };
  }, [showError]);

  return (
    <ErrorContext.Provider value={{ showError }}>
      <div className="flex min-h-screen flex-col bg-gradient-to-br from-slate-50 to-slate-100">
        {/* Header */}
        <header className="border-b border-slate-200 bg-white shadow-sm">
          <div className="container mx-auto px-4 py-4">
            <h1 className="text-2xl font-bold text-slate-800">AI Assistant</h1>
            <p className="text-sm text-slate-600">Your personal AI companion</p>
          </div>
        </header>

        {/* Main Content */}
        <main className="container mx-auto flex flex-1 flex-col p-4">
          <div className="flex flex-1 flex-col rounded-lg bg-white shadow-lg">
            <div className="flex-1 p-6">
              <ChatSection />
            </div>
          </div>
        </main>

        {/* Footer */}
        <footer className="border-t border-slate-200 bg-white py-3">
          <div className="container mx-auto px-4 text-center text-xs text-slate-500">
            AI Assistant v0.1.0 - Local AI Assistant
          </div>
        </footer>
      </div>
      <ToastContainer toasts={toasts} onClose={removeToast} />
    </ErrorContext.Provider>
  );
}

export default App;
