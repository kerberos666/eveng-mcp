"""Tools module for EVE-NG MCP Server."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
    from ..core.eveng_client import EVENGClientWrapper

# Core tools (original)
from .connection import register_connection_tools
from .lab_management import register_lab_tools
from .node_management import register_node_tools
from .network_management import register_network_tools

# Advanced tools (Wave 1 - ported from CML-MCP)
from .console import register_console_tools
from .topology import register_topology_tools
from .pcap import register_pcap_tools
from .system import register_system_tools
from .link_management import register_link_tools

# Advanced tools (Wave 2 - ported from CML-MCP)
from .annotations import register_annotation_tools
from .users_groups import register_users_groups_tools
from .node_templates import register_node_template_tools


def register_tools(mcp: "FastMCP", eveng_client: "EVENGClientWrapper") -> None:
    """Register all MCP tools."""

    # --- Core tools ---
    register_connection_tools(mcp, eveng_client)
    register_lab_tools(mcp, eveng_client)
    register_node_tools(mcp, eveng_client)
    register_network_tools(mcp, eveng_client)

    # --- Advanced tools (Wave 1: console, topology, pcap, system, links) ---
    register_console_tools(mcp, eveng_client)
    register_topology_tools(mcp, eveng_client)
    register_pcap_tools(mcp, eveng_client)
    register_system_tools(mcp, eveng_client)
    register_link_tools(mcp, eveng_client)

    # --- Advanced tools (Wave 2: annotations, users/groups, node templates) ---
    register_annotation_tools(mcp, eveng_client)
    register_users_groups_tools(mcp, eveng_client)
    register_node_template_tools(mcp, eveng_client)


__all__ = ["register_tools"]
