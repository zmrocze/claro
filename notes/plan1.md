1. Set up project structure and development environment
- Create directory structure: `/frontend` (React/TypeScript), `/backend` (FastAPI), `/os_interfaces` (platform-specific implementations)
- Initialize TypeScript/Vite/React project in frontend with `npm create vite@latest frontend -- --template react-ts`
- Set up Python project with pyproject.toml, installing core dependencies: fastapi, uvicorn, pywebview, langgraph, langchain
- Configure tailwind CSS and install shadcn components
- Set up Nix flakes for reproducible builds with development shells: [x] done
2. Implement backend API with FastAPI
- Create FastAPI application with CORS middleware for frontend communication
- Implement `/chat` endpoint for message handling
- Set up Grok API integration using OpenAI-compatible client
- Implement Zep memory integration for context storage and retrieval
- Create session management for ephemeral conversation history
- Add secure API token storage using system keyring or encrypted local storage
3. Build frontend chat interface
- Install and configure llamaindex chat UI components
- Create main chat component with message history display
- Implement message input form with submit functionality
- Add message formatting for: markdown, code snippets, file views, URLs
- Style with Tailwind CSS and shadcn components for modern design
- Implement action permission dialog for user confirmation
4. Implement LangGraph agent with ReAct pattern
- Set up zero-shot ReAct agent using LangGraph
- Configure agent with Grok model endpoint
- Implement mock action tool that shows text (as placeholder)
- Create agent executor with memory context from Zep
- Add message routing between user input, agent processing, and response
5. Create OS interface abstraction layer
- Define abstract base classes for: `NotificationManager`, `TimerManager`, `PersistentStorage`
- Implement Linux version using: pystemd for timers, desktop_notifier for notifications
- Implement Android version using PyJNIus: AlarmManager, BroadcastReceiver, NotificationManager
- Create factory pattern to select implementation based on platform
- Add shared notification click handler that opens/focuses app
6. Implement notification system
- Create YAML configuration parser for notification types
- Implement notification scheduler that checks last preparation time
- Add timer creation for next day's notifications on app open
- Create LLM prompt executor for notification content generation
- Store last notification preparation time in persistent storage
- Handle notification click events to open chat with pre-filled message
7. Integrate PyWebView wrapper
- Set up PyWebView to serve the React frontend
- Configure window settings for desktop (size, title, menu)
- Configure WebView settings for Android
- Implement communication bridge between frontend and backend
- Add platform-specific main entry points for Linux and Android
8. Configure build system with Nix
- Create Nix derivation for Vite frontend build
- Set up PyInstaller derivation for Linux executable with all dependencies
- Configure Buildozer derivation for Android APK generation
- Add buildozer.spec with Android permissions and requirements
- Create build scripts that select appropriate derivation based on target platform
9. Implement persistent storage and configuration
- Create local storage manager for app state
- Implement notification configuration YAML schema with validation
- Add configuration for: notification time, frequency, LLM prompts
- Store conversation thread ID for Zep memory continuity
- Implement configuration hot-reload for development
10. Write tests and documentation
- Unit tests for: notification scheduling, OS interfaces, message formatting
- Integration tests for: chat workflow, notification triggering, Zep memory integration
- End-to-end tests using pytest and playwright for UI testing
- Create user documentation for configuration file format
- Add developer documentation for building and deploying
11. Package and prepare for distribution
- Test PyInstaller build on Linux, verify all assets are included
- Test Buildozer APK on Android emulator and physical device
- Create installation scripts for Linux (.deb/.AppImage)
- Generate signed APK for Android with keystore
- Prepare Play Store listing assets and metadata
- Set up CI/CD pipeline using Nix for reproducible builds
