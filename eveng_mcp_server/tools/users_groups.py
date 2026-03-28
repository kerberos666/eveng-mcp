"""User and group management tools for EVE-NG MCP Server.

Inspired by cml-mcp users_groups.py:
- get_cml_users / create_cml_user / delete_cml_user
- get_cml_groups / create_cml_group / delete_cml_group

Adapted for EVE-NG's user/role API.
EVE-NG has users with roles: admin, editor, viewer (no group concept in CE,
but EVE-NG PRO has user groups/tenants).
"""
import asyncio
from typing import TYPE_CHECKING, Optional
from mcp.types import TextContent
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
    from ..core.eveng_client import EVENGClientWrapper

from ..config import get_logger

logger = get_logger("UsersGroupsTools")


def register_users_groups_tools(mcp: "FastMCP", eveng_client: "EVENGClientWrapper") -> None:
    """Register user and group management tools."""

    @mcp.tool()
    async def get_eveng_users() -> list[TextContent]:
        """
        Get all users registered on the EVE-NG server.

        Retrieves the full user list including usernames, email,
        role (admin/editor/viewer), and account status.
        Inspired by cml-mcp get_cml_users.
        Requires admin privileges.
        """
        try:
            logger.info("Getting EVE-NG users")
            if not eveng_client.is_connected:
                return [TextContent(type="text", text="Not connected.")]

            users = await asyncio.to_thread(
                eveng_client.api.list_users
            )

            users_data = users.get("data", {})
            if not users_data:
                return [TextContent(type="text", text="No users found or insufficient privileges.")]

            text = f"EVE-NG Users ({len(users_data)}):\n{'=' * 50}\n\n"
            for username, user in users_data.items():
                text += f"User: {username}\n"
                text += f"  Email:  {user.get('email', 'N/A')}\n"
                text += f"  Role:   {user.get('role', 'N/A')}\n"
                text += f"  Expiry: {user.get('expiration', 'Never')}\n"
                text += f"  Pod:    {user.get('pod', 0)}\n\n"

            return [TextContent(type="text", text=text)]
        except Exception as e:
            logger.error(f"Failed to get users: {e}")
            return [TextContent(type="text", text=f"Failed to get users: {str(e)}")]

    @mcp.tool()
    async def get_eveng_user(
        username: str,
    ) -> list[TextContent]:
        """
        Get details for a specific EVE-NG user.

        Retrieves profile information for a single user by username.
        Inspired by cml-mcp get_cml_users.
        Requires admin privileges.

        Args:
            username: The EVE-NG username to look up
        """
        try:
            logger.info(f"Getting user: {username}")
            if not eveng_client.is_connected:
                return [TextContent(type="text", text="Not connected.")]

            user = await asyncio.to_thread(
                eveng_client.api.get_user,
                username
            )

            user_data = user.get("data", {})
            if not user_data:
                return [TextContent(type="text", text=f"User '{username}' not found.")]

            text = f"User: {username}\n{'=' * 40}\n"
            text += f"  Name:       {user_data.get('name', 'N/A')}\n"
            text += f"  Email:      {user_data.get('email', 'N/A')}\n"
            text += f"  Role:       {user_data.get('role', 'N/A')}\n"
            text += f"  Expiry:     {user_data.get('expiration', 'Never')}\n"
            text += f"  Pod limit:  {user_data.get('pod', 0)}\n"
            text += f"  Pnet start: {user_data.get('pnet', 0)}\n"
            text += f"  IP:         {user_data.get('ip', 'N/A')}\n"

            return [TextContent(type="text", text=text)]
        except Exception as e:
            logger.error(f"Failed to get user: {e}")
            return [TextContent(type="text", text=f"Failed to get user '{username}': {str(e)}")]

    @mcp.tool()
    async def create_eveng_user(
        username: str,
        password: str,
        email: str = "",
        name: str = "",
        role: str = "viewer",
        expiration: str = "-1",
        pod: int = 0,
    ) -> list[TextContent]:
        """
        Create a new user on the EVE-NG server.

        Adds a new user account with specified role and credentials.
        Inspired by cml-mcp create_cml_user.
        Requires admin privileges.

        Args:
            username: Login username (unique, no spaces)
            password: Login password
            email: User email address
            name: Full display name
            role: Access role - 'admin', 'editor', or 'viewer' (default: viewer)
            expiration: Account expiry as Unix timestamp or -1 for never (default: -1)
            pod: Maximum number of pods the user can run (default: 0 = unlimited)
        """
        try:
            logger.info(f"Creating user: {username} with role: {role}")
            if not eveng_client.is_connected:
                return [TextContent(type="text", text="Not connected.")]

            payload = {
                "username": username,
                "password": password,
                "email": email,
                "name": name,
                "role": role,
                "expiration": expiration,
                "pod": pod,
            }

            result = await asyncio.to_thread(
                eveng_client.api.add_user,
                username,
                payload
            )

            return [TextContent(
                type="text",
                text=(
                    f"User '{username}' created successfully.\n"
                    f"  Role:  {role}\n"
                    f"  Email: {email}\n\n"
                    f"User can now log into the EVE-NG server."
                )
            )]
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return [TextContent(type="text", text=f"Failed to create user '{username}': {str(e)}")]

    @mcp.tool()
    async def edit_eveng_user(
        username: str,
        email: Optional[str] = None,
        name: Optional[str] = None,
        role: Optional[str] = None,
        password: Optional[str] = None,
        expiration: Optional[str] = None,
    ) -> list[TextContent]:
        """
        Edit an existing EVE-NG user's properties.

        Updates one or more fields on a user account.
        Inspired by cml-mcp modify approach.
        Requires admin privileges.

        Args:
            username: The username to modify
            email: New email address (optional)
            name: New display name (optional)
            role: New role - 'admin', 'editor', or 'viewer' (optional)
            password: New password (optional)
            expiration: New expiry Unix timestamp or -1 for never (optional)
        """
        try:
            logger.info(f"Editing user: {username}")
            if not eveng_client.is_connected:
                return [TextContent(type="text", text="Not connected.")]

            payload = {}
            if email is not None:
                payload["email"] = email
            if name is not None:
                payload["name"] = name
            if role is not None:
                payload["role"] = role
            if password is not None:
                payload["password"] = password
            if expiration is not None:
                payload["expiration"] = expiration

            if not payload:
                return [TextContent(type="text", text="No fields to update provided.")]

            result = await asyncio.to_thread(
                eveng_client.api.edit_user,
                username,
                payload
            )

            updated = ", ".join(payload.keys())
            return [TextContent(
                type="text",
                text=f"User '{username}' updated successfully.\nFields changed: {updated}"
            )]
        except Exception as e:
            logger.error(f"Failed to edit user: {e}")
            return [TextContent(type="text", text=f"Failed to edit user '{username}': {str(e)}")]

    @mcp.tool()
    async def delete_eveng_user(username: str) -> list[TextContent]:
        """
        Delete a user from the EVE-NG server.

        Permanently removes the user account.
        Inspired by cml-mcp delete_cml_user.
        Requires admin privileges.

        WARNING: This action is irreversible.

        Args:
            username: The username to delete
        """
        try:
            logger.info(f"Deleting user: {username}")
            if not eveng_client.is_connected:
                return [TextContent(type="text", text="Not connected.")]

            result = await asyncio.to_thread(
                eveng_client.api.delete_user,
                username
            )

            return [TextContent(
                type="text",
                text=f"User '{username}' deleted successfully from EVE-NG server."
            )]
        except Exception as e:
            logger.error(f"Failed to delete user: {e}")
            return [TextContent(type="text", text=f"Failed to delete user '{username}': {str(e)}")]
