This is an OpenAI organization management MCP server that allows you to invite users to your OpenAI organization.

## Example Queries

Once connected to an LLM, you can ask natural language questions like:

- "What is the status of my OpenAI invite? My email is user@example.com."
- "Please invite me to the OpenAI org. My email is user@example.com."

**Security Note:** This is a naive example where users provide their own email addresses. In a production deployment, you should pass authenticated user email addresses through a secure mechanism rather than trusting user input to the LLM.

## LLM Instructions

Use this prompt when configuring your LLM to use this MCP server:

```
You are a helpful assistant who manages OpenAI organization invitations for our team.

Your capabilities:
- Check the status of pending invitations by email address
- Send new invitations with "reader" role access

Workflow:
- Always check if an invitation already exists before creating a new one
- If a user asks for an invite and already has one pending, tell them and provide the invite details
- If they need a new invite, you must have their email address - ask if they haven't provided it
- All invitations are for "reader" role access only

Be friendly and concise. If an operation fails, explain what went wrong clearly.
```

## Prerequisites

Create two restricted OpenAI admin keys at https://platform.openai.com/settings/organization/admin-keys:

1. Read key with `api.management.read` scope
2. Write key with `api.management.write` scope

(This is an OpenAI limitatino - a single restricted key cannot GET and POST the URL we need.)

## Setup

Set both OpenAI Admin API keys as environment variables:
```bash
export OPENAI_ADMIN_KEY_READ="sk-admin-your-read-key-here"
export OPENAI_ADMIN_KEY_WRITE="sk-admin-your-write-key-here"
```

Optionally, set a default project ID to automatically add invited users as members:
```bash
export OPENAI_DEFAULT_PROJECT_ID="proj_abc123..."
```

## Usage

For development with MCP inspector, run:

```
uv run mcp dev main.py
```

For use with an MCP client (eg [5ire](https://5ire.app/)), run:
```
uv run main.py
```
... and connect the client to a "remote" endpoint, `http://127.0.0.1:8000/mcp`.

## Available Tools

(see `main.py` method docstrings for details)

- `invite_reader(email)` - Invite a user to your OpenAI organization as a reader (optionally adds them to the default project if `OPENAI_DEFAULT_PROJECT_ID` is set)
- `retrieve_invite(email)` - Retrieve an invite for a specific email address
