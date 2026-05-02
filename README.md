# productlane-cli

A small, open-source command-line client for the [Productlane](https://productlane.com) REST API.

It is designed for operators and AI agents that need to inspect Productlane support threads, fetch full conversations, and send replies from a terminal or automation workflow.

> Status: early alpha. The CLI currently focuses on Productlane threads/tickets.

## Install

From a checkout:

```bash
pipx install .
# or
python -m pip install .
```

For local development:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

## Authentication

Create/copy your Productlane API key from Productlane's API settings, then set:

```bash
export PRODUCTLANE_API_KEY="pl_..."
```

You can also use `PRODUCTLANE_TOKEN` if that is already in your environment.

## Usage

List recent threads:

```bash
productlane threads list --take 20
# short alias
pl threads list --state NEW --take 20
```

Show a single thread:

```bash
pl threads get <thread-id>
```

Show a thread with its conversation:

```bash
pl threads get <thread-id> --conversation
```

Send a message to a thread:

```bash
pl threads reply <thread-id> "Thanks for reporting this — we're taking a look."
```

Update thread state or metadata:

```bash
pl threads update <thread-id> --state PROCESSED
pl threads update <thread-id> --assignee-id <user-id>
pl threads update <thread-id> --pain-level HIGH
```

Output JSON for scripting:

```bash
pl threads list --state NEW --json | jq '.threads[].id'
```

## Safety note: replies may be customer-visible

Productlane documents `POST /threads/{threadId}/messages` as sending an email or Slack message to a thread. Treat `pl threads reply` as potentially customer-visible unless your Productlane setup confirms otherwise.

## Commands

```text
pl threads list       List Productlane threads/tickets.
pl threads get        Fetch one thread, optionally including conversation.
pl threads reply      Send a message to a thread.
pl threads update     Patch thread fields like state, title, assignee, pain level.
pl raw get            Make an authenticated raw GET request to /api/v1.
pl raw post           Make an authenticated raw POST request to /api/v1.
pl raw patch          Make an authenticated raw PATCH request to /api/v1.
```

## Configuration

Environment variables:

- `PRODUCTLANE_API_KEY` or `PRODUCTLANE_TOKEN` — required for authenticated API calls
- `PRODUCTLANE_BASE_URL` — optional, defaults to `https://productlane.com/api/v1`

## Development

```bash
python -m pip install -e '.[dev]'
ruff check .
pytest
```

## License

MIT
