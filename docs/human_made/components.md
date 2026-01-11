# App executable components

App is made up of few executable components:

- main application window `claro`
- program `remember-repo`, which is called on a git repository to "remember" it
- program `git-remember-hook`, which runs after a commit in a remembered repo to
  save the update
- program `claro-notification-schedule`, which runs once daily
- program `claro-notification`, which prepares a notification with an initiating
  chat message

The application uses two key third-party online services:

- LLM
- memory

![Component Diagram](./components_diagram.png)

## remember-repo

Program `remember-repo` when called on a repository reads its content, splits it
into small semantically relevant chunks and writes chunks to the long term
memory online service. It install `git-remember-hook`.

Program `git-remember-hook` runs as post-commit hook. It gets the diff and
performs similar chunking on its content and then submits the chunks to memory.
It differentiates between file types:

- txt
- markdown
- json
- csv

and does the reasonable thing for all of these filetypes:

- for text: tries to keep sentences together
- for markdown: additionaly adds headers information
- for json: recursive splitting of lists
- for csv: row by row, adds column names

These programs are tied to an instance of `claro` by using a single instance of
memory.

## claro

`Claro` is an app with python backend and a typical web frontend opened via
pywebview.

Its core is a simple ReAct agent:

1. it queries an llm with the users prompt
2. executes tools if the llm requested, else return message to the user
3. queries llm with the tool call results
4. go back to 2

The llm queries are aided with context from the long term memory, which includes
the recent conversation history and additional arbitrary textual information
related to entities extracted from the prompt and conversation history. We use
`zep` as the memory service.

## claro-notification-schedule

This program installed by `claro` runs periodically and schedules
`claro-notification` instances to run throughout the (next) day.

When `claro-notification` runs it gets agent answer for a configured prompt and
creates a notification with answer, clicking of which brings the user to `claro`
app.
