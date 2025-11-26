import os
import textwrap
from openai import OpenAI

# This code is based on the blog post (and accompanying notebook)
# at https://developers.redhat.com/articles/2025/08/20/your-agent-your-rules-deep-dive-responses-api-llama-stack

LLAMA_STACK_URL = os.getenv("LLAMA_STACK_URL", "http://localhost:8321/v1")
LLAMA_STACK_MODEL_ID = "vertexai/google/gemini-2.5-flash"
OPENAI_INVITE_MCP_URL = "http://localhost:8000/mcp"


def print_response(response):
    # Copied from
    # https://github.com/The-AI-Alliance/llama-stack-examples/blob/main/notebooks/01-responses/responses-api.ipynb
    print(f"ID: {response.id}")
    print(f"Status: {response.status}")
    print(f"Model: {response.model}")
    print(f"Created at: {response.created_at}")
    print(f"Output items: {len(response.output)}")

    for i, output_item in enumerate(response.output):
        if len(response.output) > 1:
            print(f"\n--- Output Item {i + 1} ---")
        print(f"Output type: {output_item.type}")

        if output_item.type in ("text", "message"):
            print(f"Response content: {output_item.content[0].text}")
        elif output_item.type == "file_search_call":
            print(f"  Tool Call ID: {output_item.id}")
            print(f"  Tool Status: {output_item.status}")
            # 'queries' is a list, so we join it for clean printing
            print(f"  Queries: {', '.join(output_item.queries)}")
            # Display results if they exist, otherwise note they are empty
            print(
                f"  Results: {output_item.results if output_item.results else 'None'}"
            )
        #elif output_item.type == "mcp_list_tools":
        #    raise ValueError("mcp_list_tools not expected client-side")
        #elif output_item.type == "mcp_call":
        #    raise ValueError("mcp_call not expected client-side")
        else:
            if hasattr(output_item, "content"):
                print(f"Response content: {output_item.content}")
            else:
                print(f"Response: {output_item}")


def simple(client: OpenAI):
    response = client.responses.create(
        model=LLAMA_STACK_MODEL_ID, input="What is the capital of France?"
    )
    print_response(response)


def process_message(client: OpenAI, message: str):
    """
    Process a message using tool calling (mcp).

    message: a chat message

    Debugging:
    `curl http://localhost:8321/v1/tools | jq` shows no tools
    """
    # Can any client pass any arbitrary MCP server here? That seems risky?
    # Is there a way to lock this down so that it's defined only in LLS?
    INSTRUCTIONS = textwrap.dedent("""\
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
    """)
    response = client.responses.create(
        model=LLAMA_STACK_MODEL_ID,
        instructions=INSTRUCTIONS,
        input=message,
        tools=[
            {
                "type": "mcp",
                "server_url": OPENAI_INVITE_MCP_URL,
                "server_label": "OpenAI Invite Server",
            }
        ]
    )
    print_response(response)


def main():
    client = OpenAI(api_key="no-key-needed", base_url=LLAMA_STACK_URL)

    # simple(client)

    # Note: this acts on untrusted input!
    # A more secure way to do this: follow the guidance in
    # https://www.anthropic.com/engineering/building-effective-agents
    #
    # Probably could decompose this into a gate/router pattern.
    # See https://www.youtube.com/watch?v=bZzyPscbtI8

    #message = "What is the status of my openai invite? My email is kdreyer+test@redhat.com."
    message = "Please invite me to the openai org. My email is kdreyer+test@redhat.com."

    process_message(client, message)


if __name__ == "__main__":
    main()
