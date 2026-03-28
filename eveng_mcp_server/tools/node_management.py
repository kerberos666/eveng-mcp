"""Node management tools for EVE-NG MCP Server."""

import asyncio

import json
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
    from ..core.eveng_client import EVENGClientWrapper

from ..config import get_logger
from ..core.exceptions import EVENGAPIError


logger = get_logger("NodeManagementTools")


def _get_status_text(status: int) -> str:
    """Convert node status code to human-readable text."""
    status_map = {
        0: "Stopped",
        1: "Starting",
        2: "Running",
        3: "Stopping"
    }
    return status_map.get(status, f"Unknown ({status})")


class ListNodesArgs(BaseModel):
    """Arguments for list_nodes tool."""
    lab_path: str = Field(description="Full path to the lab (e.g., /lab_name.unl)")


class AddNodeArgs(BaseModel):
    """Arguments for add_node tool."""
    lab_path: str = Field(description="Full path to the lab (e.g., /lab_name.unl)")
    template: str = Field(description="Node template name (e.g., 'vios', 'linux', 'iol')")
    name: str = Field(default="", description="Node name (optional, auto-generated if empty)")
    node_type: str = Field(default="qemu", description="Node type (qemu, iol, dynamips)")
    left: int = Field(default=50, description="Position from left (percentage, 0-100)")
    top: int = Field(default=50, description="Position from top (percentage, 0-100)")
    delay: int = Field(default=0, description="Seconds to wait before starting node")
    console: str = Field(default="telnet", description="Console type (telnet, vnc)")
    config: str = Field(default="Unconfigured", description="Config state (Unconfigured, Saved)")
    ethernet: Optional[int] = Field(default=None, description="Number of ethernet interfaces")
    serial: Optional[int] = Field(default=None, description="Number of serial interfaces")
    image: Optional[str] = Field(default=None, description="Specific image to use")
    ram: Optional[int] = Field(default=None, description="RAM in MB")
    cpu: Optional[int] = Field(default=None, description="Number of CPUs")


class NodeControlArgs(BaseModel):
    """Arguments for node control operations."""
    lab_path: str = Field(description="Full path to the lab (e.g., /lab_name.unl)")
    node_id: str = Field(description="Node ID to control")


class BulkNodeControlArgs(BaseModel):
    """Arguments for bulk node operations."""
    lab_path: str = Field(description="Full path to the lab (e.g., /lab_name.unl)")


class GetNodeDetailsArgs(BaseModel):
    """Arguments for get_node_details tool."""
    lab_path: str = Field(description="Full path to the lab (e.g., /lab_name.unl)")
    node_id: str = Field(description="Node ID to get details for")


class DeleteNodeArgs(BaseModel):
    """Arguments for delete_node tool."""
    lab_path: str = Field(description="Full path to the lab (e.g., /lab_name.unl)")
    node_id: str = Field(description="Node ID to delete")


class ListTemplatesArgs(BaseModel):
    """Arguments for list_node_templates tool."""
    pass  # No arguments needed


def register_node_tools(mcp: "FastMCP", eveng_client: "EVENGClientWrapper") -> None:
    """Register node management tools."""

    @mcp.tool()
    async def list_node_templates(arguments: ListTemplatesArgs) -> list[TextContent]:
        """
        List available node templates in EVE-NG.

        This tool retrieves all available node templates that can be used
        to create nodes in labs, including their supported images and options.
        """
        try:
            logger.info("Listing available node templates")

            if not eveng_client.is_connected:
                return [TextContent(
                    type="text",
                    text="Not connected to EVE-NG server. Use connect_eveng_server tool first."
                )]

            # Get templates
            templates = await eveng_client.list_node_templates()

            if not templates.get('data'):
                return [TextContent(
                    type="text",
                    text="No node templates found on the server."
                )]

            # Format templates information
            templates_text = "Available Node Templates:\n\n"

            for template_name, template_info in templates['data'].items():
                templates_text += f"📦 {template_name}\n"
                templates_text += f"   Type: {template_info.get('type', 'Unknown')}\n"
                templates_text += f"   Description: {template_info.get('description', 'No description')}\n"

                # Show available images if any
                if 'listimages' in template_info and template_info['listimages']:
                    templates_text += f"   Images: {', '.join(template_info['listimages'])}\n"

                templates_text += "\n"

            return [TextContent(
                type="text",
                text=templates_text
            )]

        except Exception as e:
            logger.error(f"Failed to list node templates: {e}")
            return [TextContent(
                type="text",
                text=f"Failed to list node templates: {str(e)}"
            )]

    @mcp.tool()
    async def list_nodes(arguments: ListNodesArgs) -> list[TextContent]:
        """
        List all nodes in a lab.

        This tool retrieves information about all nodes in the specified lab,
        including their status, configuration, and connectivity.
        """
        try:
            logger.info(f"Listing nodes in lab: {arguments.lab_path}")

            if not eveng_client.is_connected:
                return [TextContent(
                    type="text",
                    text="Not connected to EVE-NG server. Use connect_eveng_server tool first."
                )]

            # Get nodes
            nodes = await eveng_client.list_nodes(arguments.lab_path)

            if not nodes.get('data'):
                return [TextContent(
                    type="text",
                    text=f"No nodes found in lab: {arguments.lab_path}"
                )]

            # Format nodes information
            nodes_text = f"Nodes in {arguments.lab_path}:\n\n"

            for node_id, node in nodes['data'].items():
                status_icon = "🟢" if node.get('status') == 2 else "🔴" if node.get('status') == 1 else "⚪"
                nodes_text += f"{status_icon} {node.get('name', f'Node {node_id}')} (ID: {node_id})\n"
                nodes_text += f"   Template: {node.get('template', 'Unknown')}\n"
                nodes_text += f"   Type: {node.get('type', 'Unknown')}\n"
                nodes_text += f"   Image: {node.get('image', 'Unknown')}\n"
                nodes_text += f"   Status: {_get_status_text(node.get('status', 0))}\n"
                nodes_text += f"   Console: {node.get('console', 'Unknown')}\n"
                nodes_text += f"   CPU: {node.get('cpu', 'Unknown')}\n"
                nodes_text += f"   RAM: {node.get('ram', 'Unknown')} MB\n"
                nodes_text += f"   Position: ({node.get('left', 0)}%, {node.get('top', 0)}%)\n"
                nodes_text += "\n"

            return [TextContent(
                type="text",
                text=nodes_text
            )]

        except Exception as e:
            logger.error(f"Failed to list nodes: {e}")
            return [TextContent(
                type="text",
                text=f"Failed to list nodes: {str(e)}"
            )]

    @mcp.tool()
    async def add_node(arguments: AddNodeArgs) -> list[TextContent]:
        """
        Add a node to a lab.

        This tool adds a new node to an existing lab with the specified
        template, configuration, and positioning. The node will be created
        but not automatically started.
        """
        try:
            logger.info(f"Adding node to lab: {arguments.lab_path}")

            if not eveng_client.is_connected:
                return [TextContent(
                    type="text",
                    text="Not connected to EVE-NG server. Use connect_eveng_server tool first."
                )]

            # Prepare node parameters
            node_params = {
                "name": arguments.name,
                "node_type": arguments.node_type,
                "left": arguments.left,
                "top": arguments.top,
                "delay": arguments.delay,
                "console": arguments.console,
                "config": arguments.config,
            }

            # Add optional parameters if specified
            if arguments.ethernet is not None:
                node_params["ethernet"] = arguments.ethernet
            if arguments.serial is not None:
                node_params["serial"] = arguments.serial
            if arguments.image is not None:
                node_params["image"] = arguments.image
            if arguments.ram is not None:
                node_params["ram"] = arguments.ram
            if arguments.cpu is not None:
                node_params["cpu"] = arguments.cpu

            # Add node
            result = await eveng_client.add_node(arguments.lab_path, arguments.template, **node_params)

            if result.get('status') == 'success':
                node_id = result.get('data', {}).get('id', 'Unknown')
                return [TextContent(
                    type="text",
                    text=f"Successfully added node to lab!\n\n"
                         f"Lab: {arguments.lab_path}\n"
                         f"Template: {arguments.template}\n"
                         f"Node ID: {node_id}\n"
                         f"Name: {arguments.name or f'Node{node_id}'}\n"
                         f"Type: {arguments.node_type}\n"
                         f"Position: ({arguments.left}%, {arguments.top}%)\n\n"
                         f"Node created successfully. Use start_node to power it on."
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"Failed to add node: {result.get('message', 'Unknown error')}"
                )]

        except Exception as e:
            logger.error(f"Failed to add node: {e}")
            return [TextContent(
                type="text",
                text=f"Failed to add node: {str(e)}"
            )]

    @mcp.tool()
    async def get_node_details(arguments: GetNodeDetailsArgs) -> list[TextContent]:
        """
        Get detailed information about a specific node.

        This tool retrieves comprehensive information about a node including
        its configuration, status, interfaces, and connectivity.
        """
        try:
            logger.info(f"Getting node details: {arguments.node_id} in {arguments.lab_path}")

            if not eveng_client.is_connected:
                return [TextContent(
                    type="text",
                    text="Not connected to EVE-NG server. Use connect_eveng_server tool first."
                )]

            # Get node details
            node = await eveng_client.get_node(arguments.lab_path, arguments.node_id)

            if not node.get('data'):
                return [TextContent(
                    type="text",
                    text=f"Node {arguments.node_id} not found in lab {arguments.lab_path}"
                )]

            node_data = node['data']
            status_icon = "🟢" if node_data.get('status') == 2 else "🔴" if node_data.get('status') == 1 else "⚪"

            # Format node information
            details_text = f"Node Details: {node_data.get('name', f'Node {arguments.node_id}')}\n\n"

            details_text += f"{status_icon} Basic Information:\n"
            details_text += f"   ID: {arguments.node_id}\n"
            details_text += f"   Name: {node_data.get('name', 'Unknown')}\n"
            details_text += f"   Template: {node_data.get('template', 'Unknown')}\n"
            details_text += f"   Type: {node_data.get('type', 'Unknown')}\n"
            details_text += f"   Image: {node_data.get('image', 'Unknown')}\n"
            details_text += f"   Status: {_get_status_text(node_data.get('status', 0))}\n\n"

            details_text += f"⚙️  Configuration:\n"
            details_text += f"   Console: {node_data.get('console', 'Unknown')}\n"
            details_text += f"   CPU: {node_data.get('cpu', 'Unknown')}\n"
            details_text += f"   RAM: {node_data.get('ram', 'Unknown')} MB\n"
            details_text += f"   Ethernet Interfaces: {node_data.get('ethernet', 'Unknown')}\n"
            details_text += f"   Serial Interfaces: {node_data.get('serial', 'Unknown')}\n"
            details_text += f"   Delay: {node_data.get('delay', 0)} seconds\n\n"

            details_text += f"📍 Position:\n"
            details_text += f"   Left: {node_data.get('left', 0)}%\n"
            details_text += f"   Top: {node_data.get('top', 0)}%\n"

            return [TextContent(
                type="text",
                text=details_text
            )]

        except Exception as e:
            logger.error(f"Failed to get node details: {e}")
            return [TextContent(
                type="text",
                text=f"Failed to get node details: {str(e)}"
            )]

    @mcp.tool()
    async def start_node(arguments: NodeControlArgs) -> list[TextContent]:
        """
        Start a specific node.

        This tool starts a node in the lab. The node must be in stopped state
        to be started successfully.
        """
        try:
            logger.info(f"Starting node {arguments.node_id} in {arguments.lab_path}")

            if not eveng_client.is_connected:
                return [TextContent(
                    type="text",
                    text="Not connected to EVE-NG server. Use connect_eveng_server tool first."
                )]

            # Start node
            result = await eveng_client.start_node(arguments.lab_path, arguments.node_id)

            if result.get('status') == 'success':
                return [TextContent(
                    type="text",
                    text=f"Successfully started node {arguments.node_id} in {arguments.lab_path}\n\n"
                         f"The node is now booting up. It may take a few moments to become fully operational."
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"Failed to start node: {result.get('message', 'Unknown error')}"
                )]

        except Exception as e:
            logger.error(f"Failed to start node: {e}")
            return [TextContent(
                type="text",
                text=f"Failed to start node: {str(e)}"
            )]

    @mcp.tool()
    async def stop_node(arguments: NodeControlArgs) -> list[TextContent]:
        """
        Stop a specific node.

        This tool stops a running node in the lab. The node will be gracefully
        shut down and its state will be preserved.
        """
        try:
            logger.info(f"Stopping node {arguments.node_id} in {arguments.lab_path}")

            if not eveng_client.is_connected:
                return [TextContent(
                    type="text",
                    text="Not connected to EVE-NG server. Use connect_eveng_server tool first."
                )]

            # Stop node
            result = await eveng_client.stop_node(arguments.lab_path, arguments.node_id)

            if result.get('status') == 'success':
                return [TextContent(
                    type="text",
                    text=f"Successfully stopped node {arguments.node_id} in {arguments.lab_path}\n\n"
                         f"The node has been shut down and its state has been preserved."
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"Failed to stop node: {result.get('message', 'Unknown error')}"
                )]

        except Exception as e:
            logger.error(f"Failed to stop node: {e}")
            return [TextContent(
                type="text",
                text=f"Failed to stop node: {str(e)}"
            )]

    @mcp.tool()
    async def start_all_nodes(arguments: BulkNodeControlArgs) -> list[TextContent]:
        """
        Start all nodes in a lab.

        This tool starts all nodes in the specified lab. Nodes will be started
        according to their configured delay settings.
        """
        try:
            logger.info(f"Starting all nodes in {arguments.lab_path}")

            if not eveng_client.is_connected:
                return [TextContent(
                    type="text",
                    text="Not connected to EVE-NG server. Use connect_eveng_server tool first."
                )]

            # Start all nodes
            result = await eveng_client.start_all_nodes(arguments.lab_path)

            if result.get('status') == 'success':
                return [TextContent(
                    type="text",
                    text=f"Successfully started all nodes in {arguments.lab_path}\n\n"
                         f"All nodes are now booting up. They may take a few moments to become fully operational."
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"Failed to start all nodes: {result.get('message', 'Unknown error')}"
                )]

        except Exception as e:
            logger.error(f"Failed to start all nodes: {e}")
            return [TextContent(
                type="text",
                text=f"Failed to start all nodes: {str(e)}"
            )]

    @mcp.tool()
    async def stop_all_nodes(arguments: BulkNodeControlArgs) -> list[TextContent]:
        """
        Stop all nodes in a lab.

        This tool stops all running nodes in the specified lab. All nodes
        will be gracefully shut down and their states preserved.
        """
        try:
            logger.info(f"Stopping all nodes in {arguments.lab_path}")

            if not eveng_client.is_connected:
                return [TextContent(
                    type="text",
                    text="Not connected to EVE-NG server. Use connect_eveng_server tool first."
                )]

            # Stop all nodes
            result = await eveng_client.stop_all_nodes(arguments.lab_path)

            if result.get('status') == 'success':
                return [TextContent(
                    type="text",
                    text=f"Successfully stopped all nodes in {arguments.lab_path}\n\n"
                         f"All nodes have been shut down and their states preserved."
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"Failed to stop all nodes: {result.get('message', 'Unknown error')}"
                )]

        except Exception as e:
            logger.error(f"Failed to stop all nodes: {e}")
            return [TextContent(
                type="text",
                text=f"Failed to stop all nodes: {str(e)}"
            )]

    @mcp.tool()
    async def wipe_node(arguments: NodeControlArgs) -> list[TextContent]:
        """
        Wipe a specific node (reset to factory state).

        This tool wipes a node, deleting all user configuration including
        startup-config, VLANs, and other settings. The next start will
        rebuild the node from the selected image.
        """
        try:
            logger.info(f"Wiping node {arguments.node_id} in {arguments.lab_path}")

            if not eveng_client.is_connected:
                return [TextContent(
                    type="text",
                    text="Not connected to EVE-NG server. Use connect_eveng_server tool first."
                )]

            # Wipe node
            result = await eveng_client.wipe_node(arguments.lab_path, arguments.node_id)

            if result.get('status') == 'success':
                return [TextContent(
                    type="text",
                    text=f"Successfully wiped node {arguments.node_id} in {arguments.lab_path}\n\n"
                         f"⚠️  All user configuration has been deleted. The node has been reset to factory state.\n"
                         f"The next start will rebuild the node from the selected image."
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"Failed to wipe node: {result.get('message', 'Unknown error')}"
                )]

        except Exception as e:
            logger.error(f"Failed to wipe node: {e}")
            return [TextContent(
                type="text",
                text=f"Failed to wipe node: {str(e)}"
            )]

    @mcp.tool()
    async def wipe_all_nodes(arguments: BulkNodeControlArgs) -> list[TextContent]:
        """
        Wipe all nodes in a lab (reset to factory state).

        This tool wipes all nodes in the lab, deleting all user configuration
        including startup-configs, VLANs, and other settings. The next start
        will rebuild all nodes from their selected images.
        """
        try:
            logger.info(f"Wiping all nodes in {arguments.lab_path}")

            if not eveng_client.is_connected:
                return [TextContent(
                    type="text",
                    text="Not connected to EVE-NG server. Use connect_eveng_server tool first."
                )]

            # Wipe all nodes
            result = await eveng_client.wipe_all_nodes(arguments.lab_path)

            if result.get('status') == 'success':
                return [TextContent(
                    type="text",
                    text=f"Successfully wiped all nodes in {arguments.lab_path}\n\n"
                         f"⚠️  All user configurations have been deleted. All nodes have been reset to factory state.\n"
                         f"The next start will rebuild all nodes from their selected images."
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"Failed to wipe all nodes: {result.get('message', 'Unknown error')}"
                )]

        except Exception as e:
            logger.error(f"Failed to wipe all nodes: {e}")
            return [TextContent(
                type="text",
                text=f"Failed to wipe all nodes: {str(e)}"
            )]

    @mcp.tool()
    async def delete_node(arguments: DeleteNodeArgs) -> list[TextContent]:
        """
        Delete a node from a lab.

        This tool permanently removes a node from the lab. All node data
        and configuration will be lost. This action cannot be undone.
        """
        try:
            logger.info(f"Deleting node {arguments.node_id} from {arguments.lab_path}")

            if not eveng_client.is_connected:
                return [TextContent(
                    type="text",
                    text="Not connected to EVE-NG server. Use connect_eveng_server tool first."
                )]

            # Delete node
            result = await eveng_client.delete_node(arguments.lab_path, arguments.node_id)

            if result.get('status') == 'success':
                return [TextContent(
                    type="text",
                    text=f"Successfully deleted node {arguments.node_id} from {arguments.lab_path}\n\n"
                         f"⚠️  The node has been permanently removed from the lab.\n"
                         f"This action cannot be undone."
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"Failed to delete node: {result.get('message', 'Unknown error')}"
                )]

        except Exception as e:
            logger.error(f"Failed to delete node: {e}")
            return [TextContent(
                type="text",
                text=f"Failed to delete node: {str(e)}"
            )]

    @mcp.tool()
    async def configure_node(
        lab_path: str,
        node_id: str,
        config: str,
    ) -> list[TextContent]:
        """
        Set the startup configuration of a node.

        Injects a startup configuration (e.g., IOS CLI commands)
        into a node. The config will be loaded when the node
        next boots. Node must be in stopped/wiped state.
        Directly inspired by cml-mcp configure_cml_node.

        This is more efficient than starting a node and sending
        CLI commands via console - use this for initial provisioning.

        Args:
            lab_path: Full path to the lab (e.g., /my_lab.unl)
            node_id: The node ID to configure
            config: The startup configuration text (e.g., IOS config commands)
        """
        try:
            logger.info(f"Configuring node {node_id} in {lab_path}")
            if not eveng_client.is_connected:
                return [TextContent(
                    type="text",
                    text="Not connected to EVE-NG server. Use connect_eveng_server tool first."
                )]

            result = await asyncio.to_thread(
                eveng_client.api.set_node_config,
                lab_path,
                node_id,
                config
            )

            config_preview = config[:200] + "..." if len(config) > 200 else config
            return [TextContent(
                type="text",
                text=(
                    f"Startup config set for node {node_id} in {lab_path}.\n\n"
                    f"Config preview (first 200 chars):\n{config_preview}\n\n"
                    f"The configuration will be loaded on next node start."
                )
            )]
        except Exception as e:
            logger.error(f"Failed to configure node: {e}")
            return [TextContent(
                type="text",
                text=f"Failed to configure node {node_id}: {str(e)}"
            )]

    @mcp.tool()
    async def get_node_startup_config(
        lab_path: str,
        node_id: str,
    ) -> list[TextContent]:
        """
        Get the current startup configuration of a node.

        Retrieves the stored startup configuration text for a
        node. Useful for viewing what config will be loaded on
        next boot, or for auditing node configurations.
        Inspired by cml-mcp configure_cml_node (read direction).

        Args:
            lab_path: Full path to the lab (e.g., /my_lab.unl)
            node_id: The node ID to read config from
        """
        try:
            logger.info(f"Getting startup config for node {node_id} in {lab_path}")
            if not eveng_client.is_connected:
                return [TextContent(
                    type="text",
                    text="Not connected to EVE-NG server. Use connect_eveng_server tool first."
                )]

            result = await asyncio.to_thread(
                eveng_client.api.get_node_config,
                lab_path,
                node_id
            )

            config_text = result.get("data", "") if isinstance(result, dict) else str(result)

            if not config_text or config_text == "Unconfigured":
                return [TextContent(
                    type="text",
                    text=f"Node {node_id} has no startup configuration (Unconfigured)."
                )]

            return [TextContent(
                type="text",
                text=(
                    f"Startup config for node {node_id} in {lab_path}:\n"
                    f"{'=' * 60}\n\n"
                    f"{config_text}"
                )
            )]
        except Exception as e:
            logger.error(f"Failed to get node config: {e}")
            return [TextContent(
                type="text",
                text=f"Failed to get startup config for node {node_id}: {str(e)}"
            )]

    @mcp.tool()
    async def wait_for_node(
        lab_path: str,
        node_id: str,
        target_status: int = 2,
        timeout_seconds: int = 120,
        poll_interval: int = 5,
    ) -> list[TextContent]:
        """
        Wait for a node to reach a specific operational status.

        Polls the node status until it reaches the target state
        or the timeout is exceeded. Useful after start_node to
        confirm the node is fully up before sending CLI commands.
        Inspired by cml-mcp start_cml_node wait_for_convergence.

        Args:
            lab_path: Full path to the lab (e.g., /my_lab.unl)
            node_id: The node ID to monitor
            target_status: Target status code (0=Stopped, 1=Starting, 2=Running, 3=Stopping)
            timeout_seconds: Max seconds to wait before giving up (default: 120)
            poll_interval: Seconds between status checks (default: 5)
        """
        try:
            logger.info(f"Waiting for node {node_id} to reach status {target_status}")
            if not eveng_client.is_connected:
                return [TextContent(
                    type="text",
                    text="Not connected to EVE-NG server. Use connect_eveng_server tool first."
                )]

            status_labels = {0: "Stopped", 1: "Starting", 2: "Running", 3: "Stopping"}
            target_label = status_labels.get(target_status, str(target_status))

            elapsed = 0
            while elapsed < timeout_seconds:
                node_resp = await eveng_client.get_node(lab_path, node_id)
                current_status = node_resp.get("data", {}).get("status", -1)

                if current_status == target_status:
                    return [TextContent(
                        type="text",
                        text=(
                            f"Node {node_id} reached status '{target_label}' "
                            f"after {elapsed} seconds."
                        )
                    )]

                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

            current_label = status_labels.get(current_status, str(current_status))
            return [TextContent(
                type="text",
                text=(
                    f"Timeout after {timeout_seconds}s waiting for node {node_id}.\n"
                    f"Current status: '{current_label}' (expected: '{target_label}')."
                )
            )]
        except Exception as e:
            logger.error(f"Failed to wait for node: {e}")
            return [TextContent(
                type="text",
                text=f"Failed to wait for node {node_id}: {str(e)}"
            )]
