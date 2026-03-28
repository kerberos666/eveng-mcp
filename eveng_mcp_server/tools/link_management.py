"""Link management tools for EVE-NG MCP Server.

Inspired by cml-mcp links.py:
- connect_two_nodes / get_all_links_for_lab / apply_link_conditioning
- start_link / stop_link (per-link enable/disable)

Adapted for EVE-NG's API: links are managed through node interfaces
and network connections. EVE-NG uses a different model than CML:
  - CML: direct node-to-node links with UUIDs
  - EVE-NG: nodes connect to bridge networks; links visible via topology
"""

import asyncio
from typing import TYPE_CHECKING, Optional
from mcp.types import TextContent
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
    from ..core.eveng_client import EVENGClientWrapper

from ..config import get_logger

logger = get_logger("LinkManagementTools")


class ConnectNodeToNetworkArgs(BaseModel):
    """Arguments for connect_node_to_network tool."""
    lab_path: str = Field(description="Full path to the lab (e.g., /my_lab.unl)")
    src_node_id: str = Field(description="Source node ID")
    src_interface: str = Field(description="Source interface label (e.g., 'e0' or '0')")
    dst_network_id: str = Field(description="Destination network/bridge ID")


class ConnectNodeToNodeArgs(BaseModel):
    """Arguments for connect_node_to_node tool."""
    lab_path: str = Field(description="Full path to the lab (e.g., /my_lab.unl)")
    src_node_id: str = Field(description="Source node ID")
    src_interface: str = Field(description="Source interface (e.g., '0')")
    dst_node_id: str = Field(description="Destination node ID")
    dst_interface: str = Field(description="Destination interface (e.g., '0')")


class LinkConditioningArgs(BaseModel):
    """Arguments for apply_link_conditioning tool."""
    lab_path: str = Field(description="Full path to the lab")
    network_id: str = Field(description="Network/bridge ID where conditioning is applied")
    bandwidth: Optional[int] = Field(default=None, description="Bandwidth limit in Kbps (0 = unlimited)")
    latency: Optional[int] = Field(default=None, description="Latency in milliseconds")
    loss: Optional[float] = Field(default=None, description="Packet loss percentage (0-100)")
    jitter: Optional[int] = Field(default=None, description="Jitter in milliseconds")


def register_link_tools(mcp: "FastMCP", eveng_client: "EVENGClientWrapper") -> None:
    """Register link management tools."""

    @mcp.tool()
    async def get_all_links_for_lab(lab_path: str) -> list[TextContent]:
        """
        Get all links (connections) in a lab.

        Returns a comprehensive view of all node-to-network and
        node-to-node connections in the lab, including link state
        and network membership.

        Inspired by cml-mcp get_all_links_for_lab.

        Args:
            lab_path: Full path to the lab (e.g., /my_lab.unl)
        """
        try:
            logger.info(f"Getting all links for lab: {lab_path}")
            if not eveng_client.is_connected:
                return [TextContent(type="text", text="Not connected.")]

            links_resp = await asyncio.to_thread(
                eveng_client.api.list_lab_links, lab_path
            )
            links = links_resp.get("data", {})

            nodes_resp = await eveng_client.list_nodes(lab_path)
            nodes = nodes_resp.get("data", {})

            nets_resp = await eveng_client.list_lab_networks(lab_path)
            networks = nets_resp.get("data", {})

            text = f"Links for lab: {lab_path}\n{'=' * 50}\n\n"

            ethernet_links = links.get("ethernet", {})
            text += f"Ethernet Connections ({len(ethernet_links)}):\n"
            for net_id, net_name in ethernet_links.items():
                net_info = networks.get(str(net_id), {})
                text += f"  Network [{net_id}] '{net_name}' - Type: {net_info.get('type', '?')}\n"

            serial_links = links.get("serial", [])
            text += f"\nSerial Connections ({len(serial_links)}):\n"
            for link in serial_links:
                text += f"  {link}\n"

            return [TextContent(type="text", text=text)]

        except Exception as e:
            logger.error(f"Failed to get links: {e}")
            return [TextContent(type="text", text=f"Failed to get links: {str(e)}")]

    @mcp.tool()
    async def connect_node_to_network(
        lab_path: str,
        src_node_id: str,
        src_interface: str,
        dst_network_id: str,
    ) -> list[TextContent]:
        """
        Connect a node interface to a network/bridge.

        Links a specific interface on a node to an existing network
        in the lab. Both the node and network must exist.

        Inspired by cml-mcp connect_two_nodes (adapted for EVE-NG topology).

        Args:
            lab_path: Full path to the lab
            src_node_id: Source node ID
            src_interface: Interface label (e.g., '0' for eth0)
            dst_network_id: Target network/bridge ID
        """
        try:
            logger.info(
                f"Connecting node {src_node_id} iface {src_interface} "
                f"to network {dst_network_id} in {lab_path}"
            )
            if not eveng_client.is_connected:
                return [TextContent(type="text", text="Not connected.")]

            result = await eveng_client.connect_node_to_cloud(
                lab_path, src_node_id, src_interface, dst_network_id
            )

            return [TextContent(
                type="text",
                text=(
                    f"Successfully connected node {src_node_id} interface {src_interface}\n"
                    f"to network {dst_network_id} in lab {lab_path}.\n\n"
                    f"Use get_lab_topology_summary to verify the connection."
                )
            )]

        except Exception as e:
            logger.error(f"Failed to connect node to network: {e}")
            return [TextContent(
                type="text",
                text=f"Failed to connect node to network: {str(e)}"
            )]

    @mcp.tool()
    async def connect_node_to_node(
        lab_path: str,
        src_node_id: str,
        src_interface: str,
        dst_node_id: str,
        dst_interface: str,
    ) -> list[TextContent]:
        """
        Connect two nodes directly (point-to-point link).

        Creates a point-to-point connection between two node interfaces.
        EVE-NG internally creates a bridge network for this connection.

        Inspired by cml-mcp connect_two_nodes.

        Args:
            lab_path: Full path to the lab
            src_node_id: Source node ID
            src_interface: Source interface label (e.g., '0')
            dst_node_id: Destination node ID
            dst_interface: Destination interface label (e.g., '0')
        """
        try:
            logger.info(
                f"Connecting node {src_node_id}:{src_interface} <-> "
                f"{dst_node_id}:{dst_interface} in {lab_path}"
            )
            if not eveng_client.is_connected:
                return [TextContent(type="text", text="Not connected.")]

            result = await eveng_client.connect_node_to_node(
                lab_path,
                src_node_id, src_interface,
                dst_node_id, dst_interface
            )

            return [TextContent(
                type="text",
                text=(
                    f"Successfully connected:\n"
                    f"  Node {src_node_id} interface {src_interface}\n"
                    f"  <--> Node {dst_node_id} interface {dst_interface}\n"
                    f"in lab {lab_path}.\n\n"
                    f"Use get_all_links_for_lab to verify."
                )
            )]

        except Exception as e:
            logger.error(f"Failed to connect nodes: {e}")
            return [TextContent(
                type="text",
                text=f"Failed to connect nodes: {str(e)}"
            )]

    @mcp.tool()
    async def apply_link_conditioning(
        lab_path: str,
        network_id: str,
        bandwidth: Optional[int] = None,
        latency: Optional[int] = None,
        loss: Optional[float] = None,
        jitter: Optional[int] = None,
    ) -> list[TextContent]:
        """
        Apply network conditioning to a lab network/bridge.

        Simulates WAN impairments on a network segment by applying
        bandwidth limits, latency, packet loss, and jitter. Useful
        for testing application behavior under degraded conditions.

        Directly inspired by cml-mcp apply_link_conditioning.
        Note: Full conditioning requires EVE-NG PRO.

        Args:
            lab_path: Full path to the lab
            network_id: Network/bridge ID to condition
            bandwidth: Bandwidth limit in Kbps (None = no change)
            latency: Added latency in ms (None = no change)
            loss: Packet loss percentage 0-100 (None = no change)
            jitter: Jitter in ms (None = no change)
        """
        try:
            logger.info(
                f"Applying link conditioning to network {network_id} in {lab_path}: "
                f"bw={bandwidth}kbps latency={latency}ms loss={loss}% jitter={jitter}ms"
            )
            if not eveng_client.is_connected:
                return [TextContent(type="text", text="Not connected.")]

            conditions = {}
            if bandwidth is not None:
                conditions["bandwidth"] = bandwidth
            if latency is not None:
                conditions["latency"] = latency
            if loss is not None:
                conditions["loss"] = loss
            if jitter is not None:
                conditions["jitter"] = jitter

            if not conditions:
                return [TextContent(
                    type="text",
                    text="No conditioning parameters specified. Provide at least one of: bandwidth, latency, loss, jitter."
                )]

            # EVE-NG network conditioning is applied via PATCH to the network endpoint
            # The exact parameter names depend on EVE-NG API version
            result = await asyncio.to_thread(
                eveng_client.api.edit_lab_network,
                lab_path,
                int(network_id),
                conditions
            )

            applied = ", ".join(f"{k}={v}" for k, v in conditions.items())
            return [TextContent(
                type="text",
                text=(
                    f"Link conditioning applied to network {network_id}:\n"
                    f"  {applied}\n\n"
                    f"Note: Conditioning requires EVE-NG PRO for full effect."
                )
            )]

        except Exception as e:
            logger.error(f"Failed to apply link conditioning: {e}")
            return [TextContent(
                type="text",
                text=f"Failed to apply link conditioning: {str(e)}"
            )]

    @mcp.tool()
    async def disconnect_node_interface(
        lab_path: str,
        node_id: str,
        interface_id: str,
    ) -> list[TextContent]:
        """
        Disconnect a node interface from any network.

        Removes the connection between a node interface and
        its current network, effectively disconnecting that link.

        Args:
            lab_path: Full path to the lab
            node_id: Node ID
            interface_id: Interface index (e.g., '0' for eth0)
        """
        try:
            logger.info(
                f"Disconnecting node {node_id} interface {interface_id} in {lab_path}"
            )
            if not eveng_client.is_connected:
                return [TextContent(type="text", text="Not connected.")]

            # Connect interface to network_id=0 means disconnected in EVE-NG
            result = await asyncio.to_thread(
                eveng_client.api.connect_node_interface,
                lab_path,
                node_id,
                interface_id,
                0  # network_id=0 = disconnected
            )

            return [TextContent(
                type="text",
                text=f"Interface {interface_id} on node {node_id} disconnected successfully."
            )]

        except Exception as e:
            logger.error(f"Failed to disconnect interface: {e}")
            return [TextContent(
                type="text",
                text=f"Failed to disconnect interface: {str(e)}"
            )]
