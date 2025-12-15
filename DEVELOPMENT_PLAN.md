# Claro App Development Plan

## Current Status (Updated: 2025-11-02)

### Completed Phases

- ✅ **Phase 1**: Foundation Setup (Complete)
- ✅ **Phase 2**: Core Backend Implementation (Complete)
- ✅ **Phase 3**: Frontend Development (Complete)
- ❌ **Phase 3.5**: Session Persistence (Not started - HIGH PRIORITY)
- ✅ **Phase 4**: OS Interface Implementation (Base complete, integration
  pending)
- ⚠️ **Phase 5**: Notification System (API complete, scheduling incomplete)
- ✅ **Phase 6**: PyWebView Integration (Complete)
- ⚠️ **Phase 7**: Build System (Nix complete, distribution packages pending)
- ⚠️ **Phase 8**: Testing Strategy (Unit/integration done, E2E pending)
- ❌ **Phase 9**: Deployment & Distribution (Not started)

### Key Architectural Achievements

1. **Memory Provider Abstraction**: Factory pattern supporting Zep + Mock
   implementations
2. **Comprehensive Error Handling**: Custom exceptions, middleware, and detailed
   documentation
3. **Session Management**: In-memory sessions with session IDs
4. **Configuration Pattern**: Single-resolution config defaults following best
   practices
5. **Rate Limiting**: SlowAPI middleware for API protection

### Known Gaps (from human_todo.md)

1. Session persistence across app restarts
2. Message context flow to LLM needs verification
3. Multi-voice chat support
4. Action approval flow with LangGraph needs verification
5. Notification timer OS integration

## Overview

Building a personal AI assistant app for Android and Linux with local execution,
featuring a chat interface and smart notifications. The app leverages LLM (Grok)
with personal context from Zep memory to provide personalized interactions.

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

## Phase 1: Foundation Setup ✅

**Status**: Complete\
**Completion Date**: Early in development

### 1.1 Project Structure ✅

```
claro/
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

### 1.2 Dependencies to Install ✅

**Status**: All core dependencies installed and configured in `pyproject.toml`
with uv.lock\
**Build System**: Using uv2nix for reproducible Python builds

**Python Backend (Actual):**

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

**Frontend (Actual):**

- react@19.1.1 (upgraded from planned 18)
- typescript@5.8.3
- vite@7.1.2 (upgraded from planned 5)
- @llamaindex/chat-ui@0.6.1 ✅
- tailwindcss@4.1.16 (upgraded from planned 3)
- shadcn/ui components ✅
- native fetch API ✅
- @hey-api/openapi-ts for type generation ✅

### 1.3 Environment Setup Questions ✅

**Status**: All questions answered and implemented

- **Q1:** How will the Grok API key be provided initially?\
  **Answer**: Environment variable via `.env` file (`.env.dev` template
  provided)

- **Q2:** What Zep instance will be used?\
  **Answer**: Configurable via `MEMORY_PROVIDER` env var. Supports both cloud
  Zep and mock memory for testing

- **Q3:** Should the app support multiple user profiles or single user only?\
  **Answer**: Single user (configured via `ZEP_USER_ID` env var)

## Phase 2: Core Backend Implementation ✅

**Status**: Complete\
**Implementation**: All core features working, with architectural improvements
beyond plan

### 2.1 FastAPI Application Structure ✅

**Actual Implementation**:

```python
# backend/main.py
**All API Endpoints**:

*Health & Static*:
- `GET /health` - Health check endpoint ✅
- `GET /{path}` - Serve static frontend files (production) ✅

*Chat* (`/api/chat`):
- `POST /api/chat/message` - Send chat message, get response ✅
- `POST /api/chat/session` - Create new session ✅
- `GET /api/chat/sessions` - List all sessions ✅
- `GET /api/chat/history/{session_id}` - Get conversation history ✅
- `DELETE /api/chat/history/{session_id}` - Delete session history ✅

*Notifications* (`/api/notifications`):
- `GET /api/notifications/config` - Get notification configuration ✅
- `POST /api/notifications/config` - Update notification configuration ✅
- `POST /api/notifications/prepare` - Schedule notifications for next day ✅
- `GET /api/notifications/scheduled` - List scheduled notifications ✅
- `DELETE /api/notifications/scheduled/{notification_id}` - Cancel notification ✅
- `POST /api/notifications/test` - Send test notification immediately ✅

*Actions* (`/api/actions`):
- `POST /api/actions/execute` - Execute action (requires confirmation) ✅
- `GET /api/actions/pending` - List pending actions awaiting confirmation ✅
- `POST /api/actions/confirm/{action_id}` - Confirm and execute action ✅
- `DELETE /api/actions/cancel/{action_id}` - Cancel pending action ✅
- `GET /api/actions/result/{action_id}` - Get action execution result ✅
- `GET /api/actions/history` - Get action execution history ✅

### 2.2 LangGraph Agent Configuration ✅

- ✅ LangGraph ReAct agent with tools: zep memory search, `mock_action`
- ✅ Memory: Zep Cloud + Mock providers
- ✅ Model: Grok via `langchain-openai`

### 2.3 Security Considerations ✅

- ✅ **API Key Storage**: `python-keyring` with `.env` fallback
  - Keyring uses OS-native secure storage (Linux: Secret Service API/libsecret, macOS: Keychain, Windows: Credential Locker)
  - **Android**: python-keyring has limited/no support - will use `.env` fallback (stored in app private storage)
  - Falls back to `.env` files if keyring unavailable
  - Helper functions: `set_api_key()`, `get_api_key()` in `backend/config.py`
- ✅ Pydantic V2 validation, rate limiting, CORS, error handling

## Phase 3: Frontend Development ✅

**Status**: Complete  
**Implementation**: Working chat UI with streaming, action dialogs, and error toasts

### 3.1 Component Architecture ✅

**Actual Implementation**:
```

App.tsx ├── Chat (main component) ✅ ├── ActionDialog (Radix UI Dialog) ✅ └──
Toast notifications (shadcn/ui) ✅

```
### 3.2 Key Features ✅

**Status**: All implemented

- ✅ Chat application with clean UI (Tailwind styling)

### 3.3 State Management ✅

**Status**: Implemented with React state + backend sessions

- ✅ Local React state for current chat messages
- ✅ Backend session management via API
- ✅ Session ID tracking
- ⚠️ **Known Gap**: No persistence across browser refresh (see Phase 3.5 below)

## Phase 3.5: Session Persistence ❌

**Status**: Not implemented  
**Priority**: High - critical for user experience  

### 3.5.1 Backend Session Storage ❌

**Current State**: Sessions stored in-memory only (`backend/sessions.py`)
- Sessions lost on app restart
- No limit on session count (memory leak potential)

**Required Implementation**:
1. ❌ Choose storage backend
   
2. ❌ Implement session persistence:
   - Save session on every message incrementally
   - Load all sessions on app start
   - Implement session cleanup (keep last 30 messages per decision Q1)

### 3.5.2 Frontend Session Restoration ❌

**Required Implementation**:
1. ❌ Load last active session on app start
2. ❌ Restore message history in UI
3. ❌ Continue conversation in same context (requires saving langgraph agent checkpoint, maybe use memorysaver)
4. ❌ Handle session selection (if multiple sessions)

**Storage Location**:
- Linux: where?
- Android: App private storage

## Phase 4: OS Interface Implementation ⚠️

**Status**: Abstract base class defined, platform implementations are stubs only  
**What's Done**: `OSInterface` ABC with method signatures  
**What's Missing**: Actual desktop-notifier (Linux) and pyjnius (Android) integration

### 4.1 Abstract Base Classes ✅

**Status**: Implemented in `os_interfaces/*`

**Implementations**:
- `linux.py`: Stub using print statements (desktop-notifier integration pending)
- `android.py`: Stub using print statements (pyjnius integration pending)

**Questions - Answered**:

- **Q6:** Should notifications persist if the app is closed?  
  **Answer**: Yes, via OS-level scheduled notifications (not yet implemented)
  
- **Q7:** What Android permissions are needed?  
  **Answer**: `INTERNET`, `POST_NOTIFICATIONS`, `SCHEDULE_EXACT_ALARM`, `RECEIVE_BOOT_COMPLETED` (to be added to buildozer.spec)

## Phase 5: Notification System ⚠️

**Status**: API and models complete, configuration and OS integration pending  
**Priority**: High - core feature

### 5.1 Configuration Schema ⚠️

{{ ... }}
# config/notifications.yaml
notifications:
  - name: "morning_checkin"
    time: "09:00" # or range: ["08:00", "10:00"]
    frequency: 1.0 # probability per day
    prompt: "Generate a friendly morning greeting asking about user's plans"

  - name: "reflection"
    time: ["20:00", "22:00"]
    frequency: 0.7
    prompt: "Create a thoughtful question about the user's day"
```

**Status**:

- ✅ Pydantic models defined (`NotificationType`, `NotificationConfig`)
- ❌ YAML file not created (`config/` directory is empty)
- ❌ File loading/saving not implemented
- ⚠️ In-memory state used for demo purposes

**TODO**:

1. Create default `config/notifications.yaml`
2. Implement YAML loading in `backend/api/notifications.py`
3. Support runtime config updates via API

### 5.2 Notification Flow ⚠️

**Planned Flow**:

1. App opens → Check last preparation timestamp
2. If new day → Schedule all notifications for tomorrow
3. Timer triggers → Generate content via LLM
4. Show notification → Click opens app with pre-filled message

**Current Status**:

- ✅ Step 1-2: `GET /api/notifications/prepare` endpoint generates notification
  schedule
- ✅ Step 3: LLM content generation works (uses Grok to generate based on
  prompt)
- ❌ Step 3: OS timer integration missing (notifications not actually scheduled
  with OS)
- ❌ Step 4: Deep link handling not implemented

**Remaining Work**:

1. Integrate `desktop-notifier` (Linux) and `pyjnius` (Android) for actual
   notifications
2. Implement timer scheduling via `os_interfaces`
3. Add deep link handler to open chat with pre-filled notification response
4. Persist notification state across app restarts
5. Handle notification retry logic if delivery fails

## Phase 6: PyWebView Integration ✅

**Status**: Complete and working\
**Implementation**: `claro_app.py` successfully wraps the web app

### 6.1 Main Entry Points ✅

**Actual Implementation** (`claro_app.py`), packaged for Linux with
`nix build .#default`!

**Note**: Android entry point should be separate when implemented

### 6.2 Frontend-Backend Bridge ⚠️

**Status**: Basic communication works, advanced features pending

- ✅ HTTP API communication (fetch/axios)
- ✅ Server-Sent Events for streaming
- ❌ PyWebView JS API not yet used (could expose native file dialogs, etc.)
- ❌ Deep link handling not implemented

**Future Enhancements**:

1. Use `webview.api` to expose Python functions to JavaScript
2. Add deep link support for notification responses
3. Expose native file picker for future file-based features

## Phase 7: Build System ⚠️

**Status**: Nix build system complete, distribution packages pending\
**Priority**: Medium - needed for distribution

### 7.1 Build Stages

1. **Frontend Build:** `nix build .#frontend` → dist/
2. **Linux Executable:** `nix build .#linux-app`
3. **Android APK:** `nix build .#android-app` → Buildozer

### 7.2 Buildozer Configuration

Used for android build.

2. Android-specific entry point (`main_android.py`)
3. APK signing keystore

**Questions - Answered**:

- **Q8:** Target Android API level?\
  **Answer**: Target API 33, Minimum API 26 (Android 8.0+, released 2017)

- **Q9:** Should the app auto-update or use app store updates only?\
  **Answer**: App store updates only (simpler, more secure)

## Phase 8: Testing Strategy ⚠️

**Status**: Basic testing in place, comprehensive coverage pending\
**Priority**: High - needed before production release

### 8.1 Test Coverage ⚠️

**Current Status**:

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

## Success Criteria

### v1.0 Linux Release

- [x] Chat interface responds ✅
- [ ] Notifications appear reliably at scheduled times ⚠️ (API done, OS
      integration pending)
- [x] App runs on Linux
- [x] Zep memory provides relevant context for conversations ✅ (working with
      cloud Zep)
- [x] Clean, maintainable codebase ✅ (good separation of concerns)
- [ ] Good test coverage ⚠️ (basic tests exist, need expansion)
- [ ] Session persistence across restarts ❌ (HIGH PRIORITY)

### v1.0 Android Release (Future)

- [ ] App runs on Android (API 26+)
- [ ] APK with all dependencies bundled
- [ ] Mobile-optimized UI
- [ ] Background notification service

## Next Immediate Steps (Updated 2025-11-02)

### For Linux v1.0 Release

**Week 1-2: Core Functionality**

1. ❌ **Implement Session Persistence** (Phase 3.5) - HIGHEST PRIORITY
   - Create `~/.local/share/claro/sessions.json` storage
   - Implement save on every message
   - Load sessions on app startup
   - Test session restoration

2. ❌ **Create Notification Configuration** (Phase 5.1)
   - Create `config/notifications.yaml` with example notifications
   - Implement YAML loading in `backend/api/notifications.py`
   - Add configuration validation

3. ❌ **Integrate OS Notifications** (Phase 5.2)
   - Integrate `desktop-notifier` for Linux
   - Implement timer scheduling in `os_interfaces/linux.py`
   - Test notification delivery

**Week 3: Testing & Polish**

4. ❌ **Expand Test Coverage** (Phase 8)
   - Mock LLM responses for tests
   - Add session persistence tests
   - Test notification flow
   - Run coverage report

### Optional/Future

- ❌ Android implementation (2-3 weeks)
- ❌ E2E tests with Playwright
- ❌ AppImage distribution
