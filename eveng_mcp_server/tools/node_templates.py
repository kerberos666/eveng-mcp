"""Node template and image definition tools for EVE-NG MCP Server.

Inspired by cml-mcp node_definitions.py:
- get_cml_node_definitions / get_node_definition_detail

Adapted for EVE-NG's template + image model.
EVE-NG uses 'templates' (node type definitions) and 'images'
(firmware/OS files). Both are discoverable via API.
"""
import asyncio
from typing import TYPE_CHECKING, Optional
from mcp.types import TextContent

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
    from ..core.eveng_client import EVENGClientWrapper

from ..config import get_logger

logger = get_logger("NodeTemplateTools")


def register_node_template_tools(mcp: "FastMCP", eveng_client: "EVENGClientWrapper") -> None:
    """Register node template and image management tools."""

    @mcp.tool()
    async def get_node_template_detail(template_name: str) -> list[TextContent]:
        """
        Get detailed information about a specific node template.

        Retrieves full template definition including default settings,
        supported configuration options, interface counts, console type,
        and available images for this template type.
        Inspired by cml-mcp get_node_definition_detail.

        Args:
            template_name: Template name (e.g., 'vios', 'iol', 'linux', 'mikrotik')
        """
        try:
            logger.info(f"Getting template detail: {template_name}")
            if not eveng_client.is_connected:
                return [TextContent(type="text", text="Not connected.")]

            templates = await eveng_client.list_node_templates()
            templates_data = templates.get("data", {})

            if template_name not in templates_data:
                available = ", ".join(sorted(templates_data.keys())[:20])
                return [TextContent(
                    type="text",
                    text=(
                        f"Template '{template_name}' not found.\n\n"
                        f"Available templates (first 20): {available}\n"
                        f"Use list_node_templates to see all templates."
                    )
                )]

            tmpl = templates_data[template_name]

            text = f"Template: {template_name}\n{'=' * 50}\n\n"
            text += f"  Description: {tmpl.get('description', 'N/A')}\n"
            text += f"  Type:        {tmpl.get('type', 'N/A')}\n"
            text += f"  Category:    {tmpl.get('category', 'N/A')}\n"
            text += f"  Vendor:      {tmpl.get('vendor', 'N/A')}\n"
            text += f"  Default CPU: {tmpl.get('cpu', 'N/A')}\n"
            text += f"  Default RAM: {tmpl.get('ram', 'N/A')} MB\n"
            text += f"  Ethernet:    {tmpl.get('ethernet', 'N/A')} interfaces\n"
            text += f"  Serial:      {tmpl.get('serial', 'N/A')} interfaces\n"
            text += f"  Console:     {tmpl.get('console', 'N/A')}\n"
            text += f"  Delay:       {tmpl.get('delay', 0)} seconds\n"

            images = tmpl.get("listimages", [])
            if images:
                text += f"\nAvailable images ({len(images)}):\n"
                for img in images:
                    text += f"  - {img}\n"
            else:
                text += "\nImages: None uploaded (upload image to /opt/unetlab/addons/)\n"

            return [TextContent(type="text", text=text)]
        except Exception as e:
            logger.error(f"Failed to get template detail: {e}")
            return [TextContent(type="text", text=f"Failed to get template detail: {str(e)}")]

    @mcp.tool()
    async def get_node_images(template_name: str) -> list[TextContent]:
        """
        Get all available images for a specific node template.

        Lists all firmware/OS images that have been uploaded for
        a given node template type. Returns image filenames that
        can be used in the 'image' parameter when adding nodes.
        Inspired by cml-mcp get_node_definition_detail image listing.

        Args:
            template_name: Template name to get images for (e.g., 'vios', 'linux')
        """
        try:
            logger.info(f"Getting images for template: {template_name}")
            if not eveng_client.is_connected:
                return [TextContent(type="text", text="Not connected.")]

            templates = await eveng_client.list_node_templates()
            tmpl_data = templates.get("data", {}).get(template_name, {})

            images = tmpl_data.get("listimages", [])

            if not images:
                return [TextContent(
                    type="text",
                    text=(
                        f"No images available for template '{template_name}'.\n\n"
                        f"To add images, upload them to the EVE-NG server at:\n"
                        f"  /opt/unetlab/addons/qemu/{template_name}-<version>/\n"
                        f"Then run: /opt/unetlab/wrappers/unl_wrapper -a fixpermissions"
                    )
                )]

            text = f"Available images for '{template_name}' ({len(images)}):\n{'=' * 50}\n\n"
            for i, img in enumerate(images, 1):
                text += f"  {i:2}. {img}\n"
            text += f"\nUse image name in add_node 'image' parameter."

            return [TextContent(type="text", text=text)]
        except Exception as e:
            logger.error(f"Failed to get images: {e}")
            return [TextContent(type="text", text=f"Failed to get images: {str(e)}")]

    @mcp.tool()
    async def search_node_templates(query: str = "") -> list[TextContent]:
        """
        Search and filter available node templates by name or type.

        Lists all available EVE-NG node templates, optionally filtered
        by a search query. Useful for finding the correct template name
        before adding nodes to a lab.
        Inspired by cml-mcp get_cml_node_definitions.

        Args:
            query: Optional search string to filter templates (e.g., 'cisco', 'linux')
                   Leave empty to list all templates.
        """
        try:
            logger.info(f"Searching node templates with query: '{query}'")
            if not eveng_client.is_connected:
                return [TextContent(type="text", text="Not connected.")]

            templates = await eveng_client.list_node_templates()
            templates_data = templates.get("data", {})

            if query:
                q = query.lower()
                filtered = {
                    k: v for k, v in templates_data.items()
                    if q in k.lower()
                    or q in v.get("description", "").lower()
                    or q in v.get("vendor", "").lower()
                    or q in v.get("category", "").lower()
                }
            else:
                filtered = templates_data

            if not filtered:
                return [TextContent(
                    type="text",
                    text=f"No templates found matching '{query}'."
                )]

            text = f"Node Templates"
            if query:
                text += f" matching '{query}'"
            text += f" ({len(filtered)} found):\n{'=' * 50}\n\n"

            for name, tmpl in sorted(filtered.items()):
                images = tmpl.get("listimages", [])
                img_count = len(images)
                text += f"  {name:<30} | {tmpl.get('description', 'N/A')[:40]:<40} | {img_count} image(s)\n"

            text += f"\nUse get_node_template_detail <name> for full info."

            return [TextContent(type="text", text=text)]
        except Exception as e:
            logger.error(f"Failed to search templates: {e}")
            return [TextContent(type="text", text=f"Failed to search templates: {str(e)}")]
