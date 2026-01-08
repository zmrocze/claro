# Claro

A personalized chatbot app.

## Connect your notes

Mark `git` repositories that you want Claro to remember. The memory will be
updated on every commit. Claro can then base answers on information contained.
Works for:

- text files
- markdown
- csv
- json

Soon more integration options (calendar, mementoDB)!

## Schedule carlo to write back

Define how you want Claro to text you with easy syntax:

```
morning_reflection:
  hours_range:
    from: "08:00"
    to: "10:00"
  calling: |
    Say something like: 
    Good morning! How are you feeling today?
    Let's take a moment to reflect on your goals for the day.
  frequency: 0.5
```

and expect a personalized message!

## Available on linux

Currently available on linux. Build with nix with
`nix build github:zmrocze/claro`.

Android version on the way!
