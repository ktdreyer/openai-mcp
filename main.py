import logging
import os
from collections.abc import AsyncIterator
from openai import AsyncOpenAI
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.utilities.logging import get_logger

# Initialize FastMCP server
mcp = FastMCP("openai", debug=True)

# Initialize OpenAI clients with admin API keys
# OpenAI requires separate keys for read vs write on invites
read_client = AsyncOpenAI(api_key=os.environ["OPENAI_ADMIN_KEY_READ"])
write_client = AsyncOpenAI(api_key=os.environ["OPENAI_ADMIN_KEY_WRITE"])

# Optional: default project to add users to when inviting
DEFAULT_PROJECT_ID = os.environ.get("OPENAI_DEFAULT_PROJECT_ID")

logger = get_logger(__name__)
logger.setLevel(level=logging.INFO)


async def _iter_invites() -> AsyncIterator[dict]:
    """
    Async generator that yields individual invites from the OpenAI organization.

    This function handles pagination automatically by making multiple API calls
    as needed. It yields one invite at a time, fetching the next page when the
    current page is exhausted.

    The OpenAI invites API returns paginated results with up to 100 invites per
    page. This generator abstracts away the pagination details, allowing callers
    to simply iterate over all invites without worrying about page boundaries.

    Usage:
        async for invite in _iter_invites():
            print(invite["email"])

    Implementation note:
        We must use the lower-level client.get() method and track our own
        pagination state because the stainless-generated OpenAI Python SDK
        does not yet provide high-level methods for organization management.

    Yields:
        dict: Individual invite objects containing id, email, role, status, etc.

    See: https://platform.openai.com/docs/api-reference/invite
    """
    after = None

    while True:
        params = {"limit": 100}
        if after:
            params["after"] = after

        response = await read_client.get(
            "/organization/invites",
            cast_to=object,
            options={"params": params}
        )

        if not isinstance(response, dict):
            return

        for invite in response.get("data", []):
            yield invite

        if not response.get("has_more"):
            return

        after = response.get("last_id")


async def _list_all_invites() -> list[dict]:
    """Fetch all invites from the OpenAI organization."""
    return [invite async for invite in _iter_invites()]


@mcp.tool()
async def invite_reader(email: str) -> dict:
    """Invite a user to the OpenAI organization as a reader.

    Args:
        email: Email address of the user to invite

    OpenAI will send an email invitation to this user. The user must click
    the link in their email inbox to accept the invite.

    Returns information about the newly-created invite for this user.
    """
    logger.info(f"inviting {email} as a reader")

    body = {"email": email, "role": "reader"}

    # Add default project if configured
    if DEFAULT_PROJECT_ID:
        body["projects"] = [{"id": DEFAULT_PROJECT_ID, "role": "member"}]
        logger.info(f"including default project {DEFAULT_PROJECT_ID}")

    # We must use the lower-level post() method because the
    # stainless-generated OpenAI Python client has no higher-level native
    # Python methods yet.
    response = await write_client.post(
        "/organization/invites",
        body=body,
        cast_to=object,
    )
    logger.info(f"invited {response['email']}, id {response['id']}")
    return {
        "id": response["id"],
        "email": response["email"],
        "role": response["role"],
        "status": response["status"],
        "invited_at": response.get("invited_at"),
        "expires_at": response.get("expires_at"),
        "accepted_at": response.get("accepted_at"),
    }


@mcp.tool()
async def retrieve_invite(email: str) -> dict | None:
    """Search for an invite for a specific email address.

    Args:
        email: Email address to search for

    If we have invited this user, this method returns data about that invite.

    If this method returns None, then no one has invited this user yet.
    """
    logger.info(f"fetching invite list to search for {email}")
    invites = await _list_all_invites()
    logger.info(f"searching {len(invites)} invites for {email}")

    for invite in invites:
        if invite.get("email") == email:
            return {
                "id": invite["id"],
                "email": invite["email"],
                "role": invite["role"],
                "status": invite["status"],
                "invited_at": invite.get("invited_at"),
                "expires_at": invite.get("expires_at"),
                "accepted_at": invite.get("accepted_at"),
            }
    return None


if __name__ == "__main__":
    # Initialize and run the server
    # For use with MCP clients inline:
    # mcp.run(transport='stdio')
    # For use with MCP clients "remotely", over http:
    mcp.run(transport="streamable-http")
