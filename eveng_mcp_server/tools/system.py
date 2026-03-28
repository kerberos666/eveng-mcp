"""System and server information tools for EVE-NG MCP Server.

Provides tools to query server status, version, and node image lists.
Inspired by cml-mcp's get_cml_statistics tool.
"""

import asyncio
from typing import TYPE_CHECKING
from mcp.types import TextContent

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
    from ..core.eveng_client import EVENGClientWrapper

from ..config import get_logger

logger = get_logger("SystemTools")


def register_system_tools(mcp: "FastMCP", eveng_client: "EVENGClientWrapper") -> None:
    """Register system management tools."""

    @mcp.tool()
    async def get_server_info() -> list[TextContent]:
        """
        Get EVE-NG server connection and configuration information.

        Returns the configured server host, port, protocol, and whether
        SSL verification is enabled. Also reports authentication status.
        """
        try:
            cfg = eveng_client.config.eveng
            connected = eveng_client.is_connected

            text = (
                f"EVE-NG Server Info:\n"
                f"{'=' * 40}\n"
                f"Host      : {cfg.host}\n"
                f"Port      : {cfg.port}\n"
                f"Protocol  : {cfg.protocol}\n"
                f"Base URL  : {cfg.base_url}\n"
                f"SSL Verify: {cfg.ssl_verify}\n"
                f"Timeout   : {cfg.timeout}s\n"
                f"Connected : {'Yes' if connected else 'No'}\n"
            )
            return [TextContent(type="text", text=text)]

        except Exception as e:
            logger.error(f"Failed to get server info: {e}")
            return [TextContent(type="text", text=f"Failed to get server info: {str(e)}")]

    @mcp.tool()
    async def list_node_images(template: str) -> list[TextContent]:
        """
        List available images for a specific node template.

        Returns all installed images/versions for a given device type
        (e.g., 'vios', 'linux', 'iol'). Use list_node_templates first
        to see available templates.

        Args:
            template: Node template name (e.g., 'vios', 'linux', 'iol')
        """
        try:
            logger.info(f"Listing images for template: {template}")
            if not eveng_client.is_connected:
                return [TextContent(
                    type="text",
                    text="Not connected. Use connect_eveng_server first."
                )]

            details = await eveng_client.node_template_detail(template)
            data = details.get("data", {})

            images = data.get("listimages", [])
            template_type = data.get("type", "Unknown")
            description = data.get("description", "No description")

            text = (
                f"Images for template '{template}':\n"
                f"{'=' * 40}\n"
                f"Type       : {template_type}\n"
                f"Description: {description}\n"
                f"Images ({len(images)}):\n"
            )
            if images:
                for img in images:
                    text += f"  - {img}\n"
            else:
                text += "  No images found. Install images in /opt/unetlab/addons/.\n"

            return [TextContent(type="text", text=text)]

        except Exception as e:
            logger.error(f"Failed to list node images: {e}")
            return [TextContent(
                type="text",
                text=f"Failed to list node images: {str(e)}"
            )]

    @mcp.tool()
    async def test_server_connection() -> list[TextContent]:
        """
        Test connectivity to the EVE-NG server.

        Attempts to connect and authenticate with the EVE-NG server
        and reports the result. Useful for verifying credentials and
        network reachability.
        """
        try:
            logger.info("Testing server connection")
            result = await eveng_client.test_connection()

            if result:
                text = (
                    f"Connection test PASSED\n"
                    f"Successfully authenticated to {eveng_client.config.eveng.base_url}"
                )
            else:
                text = (
                    f"Connection test FAILED\n"
                    f"Could not authenticate to {eveng_client.config.eveng.base_url}\n"
                    "Check your credentials and network connectivity."
                )
            return [TextContent(type="text", text=text)]

        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return [TextContent(
                type="text",
                text=f"Connection test failed: {str(e)}"
            )]
