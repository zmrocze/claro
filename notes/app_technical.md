The application has android and linux versions, the app runs locally, no remote
server.

# interface

The interface is designed with classic frontend tools:

- typescript
- vite
- react
- llamaindex chat ui components are used to design the chat interface
- tailwind styling and shadcn components are used whenever there's a need,
  design is modern and pretty

There is also a python backend, served with fastapi + uvicorn.

The frontend is tied with backend into a full app with pywebview, both on mobile
and desktop. How this work is that pywebview opens a web view on device and
there runs this web application.

The app has to be packaged into an executable. On desktop this is done with
uv2nix and npm. On mobile with buildozer. We use nix for reproducible builds, so
with nix we define derivations that run either uv2nix or buildozer.

We use langgraph or langchain framework to orchestrate agent work. Depending on
need. We use zero-shot ReAct agent execution.

We use grok (same api use as openai's). We need to figure out how the api token
is provided and securely stored for use by the application.

The agent memory layer component: zep. This is used to get context for every
model query. Every new message is sent to zep memory.

The query to llm is performed with memory context from zep. Every new message
from user or chat response is sent to zep (single thread). The most recent
conversation history is stored in an ephemeral session memory, to be displayed
in the app. There is a single, sequential conversation thread, for every
instance of the app.

notifications: The app tracks in its persistant local state the time of last
notification preparation. If that was yesterday, then the app when opened sets
timers for notifications to be sent tomorrow. The timer when the time comes
creates a notification. Clicking the notification brings the user to the app,
either by opening the app or focusing the app if it is already running. The
notification contains a message from the llm chat bot (how it is constructed is
described in config file, fully described below). Technically this is achieved
differently on linux and android. On linux the timers are set with pystemd and
notifications created with desktop_notifier. Reas the linux details in the
thread:
https://www.perplexity.ai/search/how-to-add-app-notifications-t-Zsf15z0ESPCAVtu0aqHRBQ.
On android the timers are set with alarmmanager, broadcastreceiver and
notification manager. All from python code with PyJNIus. Read the android
details in the thread:
https://www.perplexity.ai/search/how-to-achieve-what-systems-to-iy5wZkY0TretKSeXDvvyEw.
Eventhough we use different systems on mobile and desktop, we have shared
codebase where reading the local app persistant state, setting a timer, creating
a notification and reacting to the clicked notification - are abstracted away,
and two different implementations for these "os interfaces" are provided. Most
of the code is shared, only at the last step we provide two mains: one that
initializes os interfaces with android version and one that initializes with
linux version - and these are later used as entrypoints to the exexutable at
build step.

persistent state and configuration files: The app to function needs to store
some data locally persistent. The before mentioned time of last notification
preparation. This is so that whenever app is opened, it can check if today
already the notifications were prepared for tommorrow. The first time, when
notifications were not set with timers, they are. And, the configuration for
notifications content. This is a yaml file, that lists as many as user wants
notification types. Every notification type specifies: what time of the day the
notification appears (can be an hour, or random within a range), notification
frequency (can be less or more than 1 per day, probabilistic), and llm dev
prompt, that describes how the model should draft a message shown in the
notification.

Building the app: I describe the build process below, but note that we want to
wrap this build process into nix derivations. The frontend is built with vite
(first derivation). The backend serves the frontend. The python backend is build
with nix for desktop (first variant of the final derivation with the executable)
and with buildozer for android (second variant of the derivation, with the apk
exexutable for android and all the android specification files needed to put an
app into play store).

Tests: testing meaningfull app usage workflows. unit testing the more tricky or
complex functions.

Code style: clear, concise and short, straight to the point.
