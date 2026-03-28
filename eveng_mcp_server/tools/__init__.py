refactor(tools): modular registration of new console, topology, pcap and system tools
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
    from ..core.eveng_client import EVENGClientWrapper

from .connection import register_connection_tools
from .lab_management import register_lab_tools
from .node_management import register_node_tools
from .network_management import register_network_tools
from .console import register_console_tools
from .topology import register_topology_tools
from .pcap import register_pcap_tools
from .system import register_system_tools

def register_tools(mcp: "FastMCP", eveng_client: "EVENGClientWrapper") -> None:
    """Register all MCP tools."""
    
    # Core tools
    register_connection_tools(mcp, eveng_client)
    register_lab_tools(mcp, eveng_client)
    register_node_tools(mcp, eveng_client)
    register_network_tools(mcp, eveng_client)
    
    # Advanced tools (New)
    register_console_tools(mcp, eveng_client)
    register_topology_tools(mcp, eveng_client)
    register_pcap_tools(mcp, eveng_client)
    register_system_tools(mcp, eveng_client)

__all__ = ["register_tools"]
