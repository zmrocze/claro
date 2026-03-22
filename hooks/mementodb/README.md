# MementoDB → Zep Memory Hook

Sends newly created MementoDB entries to Zep's knowledge graph as JSON episodes.

## Setup

1. Open your library in MementoDB
2. Go to **Menu → Triggers → +** (add trigger)
3. Configure:
   - **Event**: Creating an entry
   - **Phase**: After saving the entry
4. Paste the contents of `send_to_zep.js` into the script editor
5. Enable the **"HTTP requests"** permission in the trigger's
   permissions/settings
6. Replace `YOUR_ZEP_API_KEY` and `YOUR_ZEP_USER_ID` with your actual
   credentials

## What gets sent

Each new entry is posted to `POST https://api.getzep.com/api/v2/graph` as a JSON
episode containing:

- **library** — name of the MementoDB library
- **entry_id** — MementoDB entry ID
- **title** / **description** / **author**
- **created** — ISO 8601 timestamp
- **fields** — all field values from `entry().values()`

## Debugging

Check MementoDB's script log output for `Zep: sent entry ...` or
`Zep: failed ...` messages.
