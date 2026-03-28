"""Console tools for EVE-NG MCP Server.

Provides Telnet-based CLI access to nodes and console log retrieval.
Inspired by cml-mcp's send_cli_command approach, adapted for EVE-NG.
"""

import asyncio
import telnetlib
import time
from typing import TYPE_CHECKING, List, Optional
from mcp.types import TextContent
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
    from ..core.eveng_client import EVENGClientWrapper

from ..config import get_logger
from ..core.exceptions import EVENGAPIError

logger = get_logger("ConsoleTools")

# ---------------------------------------------------------------------------
# Argument models
# ---------------------------------------------------------------------------

class GetNodeConsoleArgs(BaseModel):
    """Arguments for get_node_console_url tool."""
    lab_path: str = Field(description="Full path to the lab (e.g., /lab_name.unl)")
    node_id: str = Field(description="Node ID")


class SendCLICommandArgs(BaseModel):
    """Arguments for send_cli_command tool."""
    lab_path: str = Field(description="Full path to the lab (e.g., /lab_name.unl)")
    node_id: str = Field(description="Node ID to send command to")
    commands: List[str] = Field(
        description="List of CLI commands to execute on the node"
    )
    timeout: int = Field(
        default=30,
        description="Seconds to wait for command output (default: 30)"
    )
    prompt_pattern: str = Field(
        default="#",
        description="Expected CLI prompt character to detect end of output (default: #)"
    )


class GetConsoleLogArgs(BaseModel):
    """Arguments for get_console_log tool."""
    lab_path: str = Field(description="Full path to the lab (e.g., /lab_name.unl)")
    node_id: str = Field(description="Node ID")
    lines: int = Field(
        default=50,
        description="Number of output lines to capture after connecting (default: 50)"
    )
    wait_seconds: int = Field(
        default=5,
        description="Seconds to wait for output before disconnecting (default: 5)"
    )


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _extract_telnet_host_port(console_url: str, server_host: str) -> tuple[str, int]:
    """Extract host and port from EVE-NG console URL.

    EVE-NG console URLs follow the pattern: telnet://host:port
    If the URL contains the server IP, we use the configured EVE-NG host instead
    so that connections work from the MCP server perspective.
    """
    url = console_url.replace("telnet://", "").strip("/")
    if ":" in url:
        parts = url.rsplit(":", 1)
        host = parts[0] if parts[0] not in ("0.0.0.0", "127.0.0.1") else server_host
        port = int(parts[1])
    else:
        host = server_host
        port = int(url)
    return host, port


def _run_telnet_session(
    host: str,
    port: int,
    commands: List[str],
    timeout: int,
    prompt_pattern: str,
) -> str:
    """Blocking Telnet session runner (executed in thread pool)."""
    output_lines: List[str] = []
    try:
        tn = telnetlib.Telnet(host, port, timeout=timeout)

        # Wait for initial prompt
        tn.read_until(prompt_pattern.encode(), timeout=timeout)

        for cmd in commands:
            output_lines.append(f">>> {cmd}")
            tn.write(cmd.encode("ascii") + b"\n")
            # Read until we see the prompt again (end of output)
            response = tn.read_until(prompt_pattern.encode(), timeout=timeout)
            decoded = response.decode("ascii", errors="replace")
            output_lines.append(decoded)

        tn.close()
    except Exception as exc:
        output_lines.append(f"[Telnet error] {exc}")

    return "\n".join(output_lines)


def _run_telnet_log_capture(
    host: str,
    port: int,
    wait_seconds: int,
    lines: int,
) -> str:
    """Blocking Telnet log capture (executed in thread pool)."""
    try:
        tn = telnetlib.Telnet(host, port, timeout=10)
        time.sleep(wait_seconds)
        raw = tn.read_very_eager()
        tn.close()
        decoded = raw.decode("ascii", errors="replace")
        all_lines = decoded.splitlines()
        return "\n".join(all_lines[-lines:])
    except Exception as exc:
        return f"[Telnet error] {exc}"


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

def register_console_tools(mcp: "FastMCP", eveng_client: "EVENGClientWrapper") -> None:
    """Register console management tools."""

    @mcp.tool()
    async def get_node_console_url(lab_path: str, node_id: str) -> list[TextContent]:
        """
        Get the Telnet console URL for a specific node.

        Returns the console connection details (host, port, full URL)
        for connecting to a node's serial console. The node must be
        running for the console to be accessible.
        """
        try:
            logger.info(f"Getting console URL for node {node_id} in {lab_path}")
            if not eveng_client.is_connected:
                return [TextContent(
                    type="text",
                    text="Not connected to EVE-NG server. Use connect_eveng_server tool first."
                )]

            node_resp = await eveng_client.get_node(lab_path, node_id)
            node = node_resp.get("data", {})
            console_url = node.get("url", "")

            if not console_url:
                return [TextContent(
                    type="text",
                    text=(
                        f"No console URL available for node {node_id}.\n"
                        "Make sure the node is running and has a console type configured."
                    )
                )]

            host, port = _extract_telnet_host_port(
                console_url, eveng_client.config.eveng.host
            )

            text = (
                f"Console URL for node {node.get('name', node_id)}:\n\n"
                f"  Full URL : {console_url}\n"
                f"  Host     : {host}\n"
                f"  Port     : {port}\n"
                f"  Type     : {node.get('console', 'telnet')}\n\n"
                f"Connect with: telnet {host} {port}"
            )
            return [TextContent(type="text", text=text)]

        except Exception as e:
            logger.error(f"Failed to get console URL: {e}")
            return [TextContent(type="text", text=f"Failed to get console URL: {str(e)}")]

    @mcp.tool()
    async def send_cli_command(
        lab_path: str,
        node_id: str,
        commands: List[str],
        timeout: int = 30,
        prompt_pattern: str = "#",
    ) -> list[TextContent]:
        """
        Send CLI commands to a node via Telnet and return the output.

        This tool connects to a running node's Telnet console, executes
        each command in the list sequentially, captures the output, and
        returns it. Ideal for verifying configurations, running show
        commands, or automating CLI tasks on routers/switches.

        Prerequisites:
          - Node must be running (use start_node first).
          - Node must have telnet console type configured.
          - EVE-NG server must be reachable on the console port.

        Args:
            lab_path: Full path to the lab (e.g., /my_lab.unl)
            node_id: ID of the target node
            commands: List of CLI commands (e.g., ["show version", "show ip int brief"])
            timeout: Max seconds to wait per command (default 30)
            prompt_pattern: String that marks end of output (default "#")
        """
        try:
            logger.info(f"Sending CLI commands to node {node_id} in {lab_path}")
            if not eveng_client.is_connected:
                return [TextContent(
                    type="text",
                    text="Not connected to EVE-NG server. Use connect_eveng_server tool first."
                )]

            # Get node console URL
            node_resp = await eveng_client.get_node(lab_path, node_id)
            node = node_resp.get("data", {})
            console_url = node.get("url", "")

            if not console_url:
                return [TextContent(
                    type="text",
                    text=(
                        f"No console URL available for node {node_id}.\n"
                        "Ensure the node is running and has telnet console enabled."
                    )
                )]

            host, port = _extract_telnet_host_port(
                console_url, eveng_client.config.eveng.host
            )

            # Execute commands in thread pool (Telnet is blocking)
            output = await asyncio.to_thread(
                _run_telnet_session, host, port, commands, timeout, prompt_pattern
            )

            result_text = (
                f"CLI Output for node {node.get('name', node_id)} "
                f"(ID: {node_id}) | {host}:{port}\n"
                f"{'=' * 60}\n"
                f"{output}\n"
                f"{'=' * 60}\n"
                f"Commands sent: {len(commands)}"
            )
            return [TextContent(type="text", text=result_text)]

        except Exception as e:
            logger.error(f"Failed to send CLI command: {e}")
            return [TextContent(type="text", text=f"Failed to send CLI command: {str(e)}")]

    @mcp.tool()
    async def get_console_log(
        lab_path: str,
        node_id: str,
        lines: int = 50,
        wait_seconds: int = 5,
    ) -> list[TextContent]:
        """
        Capture recent console output from a running node.

        Connects to the node's Telnet console, waits briefly for output
        to accumulate, then reads and returns the last N lines. Useful
        for checking boot messages, interface status changes, or recent
        syslog entries without sending explicit commands.

        Args:
            lab_path: Full path to the lab (e.g., /my_lab.unl)
            node_id: ID of the target node
            lines: Number of trailing lines to return (default 50)
            wait_seconds: Seconds to wait for output (default 5)
        """
        try:
            logger.info(f"Capturing console log for node {node_id} in {lab_path}")
            if not eveng_client.is_connected:
                return [TextContent(
                    type="text",
                    text="Not connected to EVE-NG server. Use connect_eveng_server tool first."
                )]

            node_resp = await eveng_client.get_node(lab_path, node_id)
            node = node_resp.get("data", {})
            console_url = node.get("url", "")

            if not console_url:
                return [TextContent(
                    type="text",
                    text=(
                        f"No console URL available for node {node_id}.\n"
                        "Ensure the node is running."
                    )
                )]

            host, port = _extract_telnet_host_port(
                console_url, eveng_client.config.eveng.host
            )

            log_output = await asyncio.to_thread(
                _run_telnet_log_capture, host, port, wait_seconds, lines
            )

            result_text = (
                f"Console Log for node {node.get('name', node_id)} "
                f"(ID: {node_id}) | last {lines} lines\n"
                f"{'=' * 60}\n"
                f"{log_output}\n"
                f"{'=' * 60}"
            )
            return [TextContent(type="text", text=result_text)]

        except Exception as e:
            logger.error(f"Failed to get console log: {e}")
            return [TextContent(type="text", text=f"Failed to get console log: {str(e)}")]
