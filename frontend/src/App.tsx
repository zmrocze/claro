import './App.css'
import { ChatSection } from './components/chat'

function App() {
  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-br from-slate-50 to-slate-100">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white shadow-sm">
        <div className="container mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-slate-800">Carlo AI Assistant</h1>
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
          Carlo v0.1.0 - Local AI Assistant
        </div>
      </footer>
    </div>
  )
}

export default App
