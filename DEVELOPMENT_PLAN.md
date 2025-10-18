# Carlo App Development Plan

## Overview
Building a personal AI assistant app for Android and Linux with local execution, featuring a chat interface and smart notifications. The app leverages LLM (Grok) with personal context from Zep memory to provide personalized interactions.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     PyWebView Wrapper                    │
├─────────────────────────────────────────────────────────┤
│  Frontend (React/TS)  │  Backend (FastAPI)              │
│  - Chat UI            │  - LangGraph Agent              │
│  - Notification UI    │  - Zep Memory                   │
│                       │  - Grok LLM Client              │
├───────────────────────┼─────────────────────────────────┤
│                 OS Interface Abstraction                 │
│         Linux Implementation │ Android Implementation   │
└─────────────────────────────────────────────────────────┘
```

## Phase 1: Foundation Setup

### 1.1 Project Structure
```
carlo/
├── frontend/               # React/TypeScript/Vite app
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── hooks/         # Custom React hooks
│   │   └── styles/        # Tailwind configurations
│   └── package.json
├── backend/               # Python FastAPI backend
│   ├── api/              # API endpoints
│   ├── agent/            # LangGraph agent logic
│   ├── memory/           # Zep integration
│   └── main.py
├── os_interfaces/        # Platform-specific code
│   ├── base.py          # Abstract base classes
│   ├── linux.py         # Linux implementation
│   └── android.py       # Android implementation
├── config/               # Configuration files
│   └── notifications.yaml
├── builds/               # Build configurations
│   ├── pyinstaller.spec
│   └── buildozer.spec
├── nix/                  # Nix derivations
│   ├── frontend.nix
│   ├── linux-build.nix
│   └── android-build.nix
└── tests/
```

### 1.2 Dependencies to Install

**Python Backend:**
- fastapi==0.104.1
- uvicorn[standard]==0.24.0
- pywebview==4.3.3
- langgraph==0.0.32
- langchain==0.1.0
- openai==1.3.0 (for Grok API)
- zep-python==2.0.0
- pyyaml==6.0.1
- python-keyring==24.3.0
- desktop-notifier==3.5.0 (Linux)
- pystemd==0.13.0 (Linux)
- pyjnius==1.5.0 (Android)

**Frontend:**
- react@18
- typescript@5
- vite@5
- @llamaindex/chat-ui
- tailwindcss@3
- shadcn/ui components
- axios or fetch API

### 1.3 Environment Setup Questions
- **Q1:** How will the Grok API key be provided initially? (environment variable, user input, config file?)
- **Q2:** What Zep instance will be used? (local Docker, cloud, embedded?)
- **Q3:** Should the app support multiple user profiles or single user only?

## Phase 2: Core Backend Implementation

### 2.1 FastAPI Application Structure
```python
# backend/main.py
app = FastAPI()
app.add_middleware(CORSMiddleware, ...)

@app.post("/chat")
async def chat_endpoint(message: ChatMessage) -> ChatResponse:
    # 1. Add message to Zep memory
    # 2. Get context from Zep
    # 3. Run LangGraph agent
    # 4. Return response
    
@app.get("/notifications/prepare")
async def prepare_notifications() -> NotificationStatus:
    # Generate and schedule notifications

@app.post("/action/execute")
async def execute_action(action: ActionRequest) -> ActionResult:
    # Execute user-approved actions
```

### 2.2 LangGraph Agent Configuration
- Implement zero-shot ReAct pattern
- Tools: MockAction (initially), expandable tool registry
- Memory: Zep context injection in system prompt
- Model: Grok with OpenAI-compatible client

### 2.3 Security Considerations
- API key storage: Use `python-keyring` for secure storage
- Input validation: Pydantic models for all endpoints
- Rate limiting: Implement request throttling

## Phase 3: Frontend Development

### 3.1 Component Architecture
```
App.tsx
├── ChatContainer/
│   ├── MessageList/
│   │   ├── Message/ (with formatting support)
│   │   └── ActionDialog/
│   └── InputForm/
└── NotificationHandler/
```

### 3.2 Key Features
- Chat application as describe in ux.md
- Real-time message streaming
- Rich text formatting (Markdown, code highlighting)
- Action confirmation dialogs
- Responsive design for mobile/desktop

### 3.3 State Management
- Session memory in local state

## Phase 4: OS Interface Implementation

### 4.1 Abstract Base Classes
```python
# os_interfaces/base.py
class NotificationManager(ABC):
    @abstractmethod
    def create_notification(self, title: str, body: str, data: dict): ...
    
class TimerManager(ABC):
    @abstractmethod
    def schedule_timer(self, time: datetime, callback: Callable): ...
    
class PersistentStorage(ABC):
    @abstractmethod
    def get(self, key: str) -> Any: ...
    @abstractmethod
    def set(self, key: str, value: Any): ...
```

### 4.2 Platform Detection and Factory
```python
def create_os_interface():
    if sys.platform == "linux":
        return LinuxInterface()
    elif "ANDROID_ROOT" in os.environ:
        return AndroidInterface()
```

**Questions:**
- **Q6:** Should notifications persist if the app is closed?
- **Q7:** What Android permissions are needed? (WAKE_LOCK, RECEIVE_BOOT_COMPLETED, etc.)

## Phase 5: Notification System

### 5.1 Configuration Schema
```yaml
# config/notifications.yaml
notifications:
  - name: "morning_checkin"
    time: "09:00"  # or range: ["08:00", "10:00"]
    frequency: 1.0  # probability per day
    prompt: "Generate a friendly morning greeting asking about user's plans"
    
  - name: "reflection"
    time: ["20:00", "22:00"]
    frequency: 0.7
    prompt: "Create a thoughtful question about the user's day"
```

### 5.2 Notification Flow
1. App opens → Check last preparation timestamp
2. If new day → Schedule all notifications for tomorrow
3. Timer triggers → Generate content via LLM
4. Show notification → Click opens app with pre-filled message

## Phase 6: PyWebView Integration

### 6.1 Main Entry Points
```python
# main_linux.py
def main():
    os_interface = LinuxInterface()
    start_backend()
    webview.create_window("Carlo", "http://localhost:8000")
    webview.start()

# main_android.py  
def main():
    os_interface = AndroidInterface()
    # Android-specific WebView setup
```

### 6.2 Frontend-Backend Bridge
- Use PyWebView's JS API for native features
- Handle deep links from notifications

## Phase 7: Build System with Nix

### 7.1 Build Stages
1. **Frontend Build:** `nix build .#frontend` → dist/
2. **Linux Executable:** `nix build .#linux-app` → PyInstaller
3. **Android APK:** `nix build .#android-app` → Buildozer

### 7.2 Buildozer Configuration
```ini
[app]
title = Carlo
package.name = carlo
source.dir = .
requirements = python3,fastapi,uvicorn,pywebview,...
android.permissions = INTERNET,POST_NOTIFICATIONS,SCHEDULE_EXACT_ALARM
```

**Questions:**
- **Q8:** Target Android API level? (minimum and target)
- **Q9:** Should the app auto-update or use app store updates only?

## Phase 8: Testing Strategy

### 8.1 Test Coverage
- **Unit Tests:** OS interfaces, notification scheduler, message formatting
- **Integration Tests:** API endpoints, Zep integration, LLM mocking
- **E2E Tests:** Full chat flow, notification triggering

### 8.2 Test Tools
- pytest for Python tests
- Jest/Vitest for frontend
- Playwright for E2E testing

## Phase 9: Deployment & Distribution

### 9.1 Linux Distribution
- Create .AppImage for universal Linux compatibility
- Optional: .deb/.rpm packages
- Desktop entry file for app launcher

### 9.2 Android Distribution
- Sign APK with release keystore
- Prepare Play Store assets (icons, screenshots, descriptions)
- Set up beta testing track

## Implementation Order

1. **Week 1-2:** Basic backend with FastAPI and LangGraph agent
2. **Week 2-3:** Frontend chat interface with llamaindex components
3. **Week 3-4:** OS interface abstraction and Linux implementation
4. **Week 4-5:** Notification system and configuration
5. **Week 5-6:** PyWebView integration and packaging
6. **Week 6-7:** Android implementation and Buildozer setup
7. **Week 7-8:** Testing, refinement, and documentation
8. **Week 8-9:** Nix build system and CI/CD
9. **Week 9-10:** Distribution preparation and release

## Open Technical Decisions

1. **Memory Persistence:** How much conversation history to keep locally vs in Zep? A: send all to zep, keep locally as much as is feasible without complex state management, up to 500 messages.
2. **Offline Mode:** Should the app work offline with degraded functionality? A: when offline open "offline" page which only shows past conversation history
3. **Multi-device Sync:** Should user data sync across devices? A: no. (because it implicitly syncs because of zep, no further syncing on our side)
4. **Action System:** What real actions should be implemented beyond mock? A: no for now.
5. **Privacy:** How to handle sensitive data in notifications? A: no specific handling, just show it
6. **Performance:** Message streaming vs batch responses? A: make an informed decision
7. **Updates:** How to handle app updates with persistent data? A: no specific handling. if persistant data cannot be parsed, inform with error message.

## Risk Mitigation

- **Buildozer Complexity:** Start Android build early, test on multiple devices
- **Notification Reliability:** Implement fallback mechanisms for timer failures
- **API Key Security:** Never commit keys, use secure storage from day 1
- **Cross-platform Issues:** Abstract all platform-specific code properly
- **Memory Management:** Monitor Zep storage costs and implement cleanup
- **Handle errors gracefully:** Log errors to logs, show comprehensive and clean error description to the user, in the ui.

## Success Criteria

- [ ] Chat interface responds within 2 seconds
- [ ] Notifications appear reliably at scheduled times
- [ ] App runs on Linux (Ubuntu 22.04+) and Android (API 26+)
- [ ] Single executable/APK with all dependencies bundled
- [ ] Zep memory provides relevant context for conversations
- [ ] Clean, maintainable codebase with good test coverage

## Next Immediate Steps

1. Update `pyproject.toml` with all Python dependencies
2. Initialize frontend with Vite: `npm create vite@latest frontend -- --template react-ts`
3. Create basic FastAPI server with health check endpoint
4. Set up Grok API client with test connection
5. Implement basic Zep memory integration
6. Create OS interface abstract base classes
