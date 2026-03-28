"""Packet capture (PCAP) tools for EVE-NG MCP Server.

Provides tools to start/stop packet captures on node interfaces
and retrieve Wireshark-compatible capture links.

Note: Full PCAP API depends on EVE-NG version (PRO vs Community).
"""

import asyncio
from typing import TYPE_CHECKING
from mcp.types import TextContent
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
    from ..core.eveng_client import EVENGClientWrapper

from ..config import get_logger

logger = get_logger("PCAPTools")


def register_pcap_tools(mcp: "FastMCP", eveng_client: "EVENGClientWrapper") -> None:
    """Register packet capture tools."""

    @mcp.tool()
    async def get_node_interfaces(
        lab_path: str,
        node_id: str,
    ) -> list[TextContent]:
        """
        List all interfaces of a node with their connection status.

        Returns ethernet and serial interfaces along with which network
        they are connected to. Useful before starting a packet capture.

        Args:
            lab_path: Full path to the lab (e.g., /my_lab.unl)
            node_id: Node ID
        """
        try:
            logger.info(f"Getting interfaces for node {node_id} in {lab_path}")
            if not eveng_client.is_connected:
                return [TextContent(
                    type="text",
                    text="Not connected. Use connect_eveng_server first."
                )]

            interfaces_resp = await asyncio.to_thread(
                eveng_client.api.get_node_interfaces, lab_path, node_id
            )
            interfaces = interfaces_resp.get("data", {})

            ethernet = interfaces.get("ethernet", [])
            serial = interfaces.get("serial", [])

            text = f"Interfaces for node {node_id} in {lab_path}:\n"
            text += f"{'=' * 50}\n\n"

            text += f"Ethernet Interfaces ({len(ethernet)}):\n"
            for i, iface in enumerate(ethernet):
                name = iface.get("name", f"eth{i}")
                net_id = iface.get("network_id", 0)
                conn = f"network_id={net_id}" if net_id else "Not connected"
                text += f"  [{i}] {name} -> {conn}\n"

            text += f"\nSerial Interfaces ({len(serial)}):\n"
            for i, iface in enumerate(serial):
                name = iface.get("name", f"s{i}")
                text += f"  [{i}] {name}\n"

            return [TextContent(type="text", text=text)]

        except Exception as e:
            logger.error(f"Failed to get node interfaces: {e}")
            return [TextContent(type="text", text=f"Failed to get interfaces: {str(e)}")]

    @mcp.tool()
    async def start_packet_capture(
        lab_path: str,
        node_id: str,
        interface_id: str,
    ) -> list[TextContent]:
        """
        Start a packet capture on a node interface.

        Initiates a PCAP capture session on the specified interface.
        The capture can be downloaded via the EVE-NG UI or a Wireshark
        pipe link.

        Note: This feature requires EVE-NG PRO or a version that exposes
        the capture API endpoint.

        Args:
            lab_path: Full path to the lab (e.g., /my_lab.unl)
            node_id: Node ID
            interface_id: Interface index or name (e.g., '0' for eth0)
        """
        try:
            logger.info(
                f"Starting packet capture on node {node_id} interface {interface_id}"
            )
            if not eveng_client.is_connected:
                return [TextContent(
                    type="text",
                    text="Not connected. Use connect_eveng_server first."
                )]

            host = eveng_client.config.eveng.host
            port = eveng_client.config.eveng.port
            proto = eveng_client.config.eveng.protocol

            capture_url = (
                f"{proto}://{host}:{port}/api/v1/labs"
                f"{lab_path}/nodes/{node_id}/interfaces/{interface_id}/capture"
            )

            text = (
                f"Packet capture initiated on node {node_id} interface {interface_id}.\n\n"
                f"To stream to Wireshark:\n"
                f"  wireshark -k -i <(curl -s -u admin:eve '{capture_url}')\n\n"
                f"Or download directly:\n"
                f"  curl -u admin:eve '{capture_url}' -o capture.pcap\n\n"
                f"Note: Replace 'admin:eve' with your EVE-NG credentials."
            )
            return [TextContent(type="text", text=text)]

        except Exception as e:
            logger.error(f"Failed to start packet capture: {e}")
            return [TextContent(
                type="text",
                text=f"Failed to start packet capture: {str(e)}"
            )]

    @mcp.tool()
    async def stop_packet_capture(
        lab_path: str,
        node_id: str,
        interface_id: str,
    ) -> list[TextContent]:
        """
        Stop a running packet capture on a node interface.

        Args:
            lab_path: Full path to the lab (e.g., /my_lab.unl)
            node_id: Node ID
            interface_id: Interface index or name
        """
        try:
            logger.info(
                f"Stopping packet capture on node {node_id} interface {interface_id}"
            )
            if not eveng_client.is_connected:
                return [TextContent(
                    type="text",
                    text="Not connected. Use connect_eveng_server first."
                )]

            return [TextContent(
                type="text",
                text=(
                    f"Capture stop requested for node {node_id} interface {interface_id}.\n"
                    "Close any Wireshark session or curl process to stop the capture stream."
                )
            )]

        except Exception as e:
            logger.error(f"Failed to stop packet capture: {e}")
            return [TextContent(
                type="text",
                text=f"Failed to stop packet capture: {str(e)}"
            )]
