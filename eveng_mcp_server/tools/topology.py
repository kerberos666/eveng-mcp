"""Topology and lab export tools for EVE-NG MCP Server."""

import asyncio
from typing import TYPE_CHECKING
from mcp.types import TextContent
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
    from ..core.eveng_client import EVENGClientWrapper

from ..config import get_logger

logger = get_logger("TopologyTools")


def register_topology_tools(mcp: "FastMCP", eveng_client: "EVENGClientWrapper") -> None:
    """Register topology management tools."""

    @mcp.tool()
    async def export_lab_topology(lab_path: str) -> list[TextContent]:
        """
        Export a lab topology summary (UNL metadata).

        Returns metadata about the lab including name, node count and
        network count. Useful for backup/documentation purposes.

        Args:
            lab_path: Full path to the lab (e.g., /my_lab.unl)
        """
        try:
            logger.info(f"Exporting topology for lab: {lab_path}")
            if not eveng_client.is_connected:
                return [TextContent(
                    type="text",
                    text="Not connected. Use connect_eveng_server first."
                )]

            lab_data = await eveng_client.get_lab(lab_path)
            data = lab_data.get("data", {})

            nodes_resp = await eveng_client.list_nodes(lab_path)
            nodes = nodes_resp.get("data", {})

            nets_resp = await eveng_client.list_lab_networks(lab_path)
            networks = nets_resp.get("data", {})

            text = (
                f"Topology Export: {lab_path}\n"
                f"{'=' * 50}\n"
                f"Lab Name    : {data.get('name', 'Unknown')}\n"
                f"Author      : {data.get('author', 'Unknown')}\n"
                f"Version     : {data.get('version', 'Unknown')}\n"
                f"Description : {data.get('description', 'None')}\n"
                f"Nodes       : {len(nodes)}\n"
                f"Networks    : {len(networks)}\n\n"
                "Node List:\n"
            )
            for node_id, node in nodes.items():
                text += f"  [{node_id}] {node.get('name', 'Unknown')} - {node.get('template', '?')} ({node.get('image', '?')})\n"

            text += "\nNetwork List:\n"
            for net_id, net in networks.items():
                text += f"  [{net_id}] {net.get('name', 'Unknown')} - Type: {net.get('type', '?')}\n"

            return [TextContent(type="text", text=text)]

        except Exception as e:
            logger.error(f"Failed to export topology: {e}")
            return [TextContent(type="text", text=f"Failed to export topology: {str(e)}")]

    @mcp.tool()
    async def get_lab_topology_summary(lab_path: str) -> list[TextContent]:
        """
        Get a concise visual summary of the lab topology.

        Shows all nodes and which networks/cloud segments they are connected
        to. Provides a quick mental map of the lab without opening EVE-NG.

        Args:
            lab_path: Full path to the lab (e.g., /my_lab.unl)
        """
        try:
            logger.info(f"Getting topology summary for: {lab_path}")
            if not eveng_client.is_connected:
                return [TextContent(type="text", text="Not connected.")]

            nodes_resp = await eveng_client.list_nodes(lab_path)
            nodes = nodes_resp.get("data", {})

            nets_resp = await eveng_client.list_lab_networks(lab_path)
            networks = nets_resp.get("data", {})

            summary = f"Topology Summary: {lab_path}\n{'=' * 50}\n\n"
            summary += f"Nodes ({len(nodes)}):\n"

            status_map = {0: "Stopped", 1: "Starting", 2: "Running", 3: "Stopping"}
            for node_id, node in nodes.items():
                status = status_map.get(node.get("status", 0), "Unknown")
                icon = "==>" if node.get("status") == 2 else "---"
                summary += (
                    f"  {icon} [{node_id}] {node.get('name', 'Unknown')} "
                    f"| {node.get('template', '?')} | {status}\n"
                )

            summary += f"\nNetworks ({len(networks)}):\n"
            for net_id, net in networks.items():
                summary += f"  [net{net_id}] {net.get('name', 'Unknown')} ({net.get('type', '?')})\n"

            return [TextContent(type="text", text=summary)]

        except Exception as e:
            logger.error(f"Failed to get topology summary: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]
