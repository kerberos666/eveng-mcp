"""Annotation management tools for EVE-NG MCP Server.

Inspired by cml-mcp annotations.py:
- get_annotations_for_lab / add_annotation_to_lab / delete_annotation_from_lab

EVE-NG supports text annotations (labels) on the canvas.
Adapted from CML's multi-shape annotation system to EVE-NG's simpler model.
"""
import asyncio
from typing import TYPE_CHECKING, Optional, Literal
from mcp.types import TextContent
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP
    from ..core.eveng_client import EVENGClientWrapper

from ..config import get_logger

logger = get_logger("AnnotationTools")


class LabAnnotation(BaseModel):
    """An annotation (label) on the EVE-NG lab canvas."""
    type: Literal["text"] = Field(default="text", description="Annotation type (EVE-NG supports 'text' labels)")
    data: str = Field(description="Text content of the annotation (max 4096 chars)")
    x: int = Field(default=50, description="X position on canvas (percentage 0-100)")
    y: int = Field(default=50, description="Y position on canvas (percentage 0-100)")


def register_annotation_tools(mcp: "FastMCP", eveng_client: "EVENGClientWrapper") -> None:
    """Register annotation management tools."""

    @mcp.tool()
    async def get_lab_annotations(lab_path: str) -> list[TextContent]:
        """
        Get all text annotations (labels) on the lab canvas.

        Retrieves all annotation objects placed on the EVE-NG lab
        diagram, including their text content and position.
        Inspired by cml-mcp get_annotations_for_cml_lab.

        Args:
            lab_path: Full path to the lab (e.g., /my_lab.unl)
        """
        try:
            logger.info(f"Getting annotations for lab: {lab_path}")
            if not eveng_client.is_connected:
                return [TextContent(type="text", text="Not connected.")]

            lab_resp = await eveng_client.get_lab(lab_path)
            lab_data = lab_resp.get("data", {})
            annotations = lab_data.get("objects", {})

            if not annotations:
                return [TextContent(type="text", text=f"No annotations found in lab: {lab_path}")]

            text = f"Annotations for lab: {lab_path}\n{'=' * 50}\n\n"
            for ann_id, ann in annotations.items():
                text += f"[{ann_id}] \"{ann.get('data', '')}\""
                text += f" @ ({ann.get('x', '?')}%, {ann.get('y', '?')}%)\n"

            return [TextContent(type="text", text=text)]
        except Exception as e:
            logger.error(f"Failed to get annotations: {e}")
            return [TextContent(type="text", text=f"Failed to get annotations: {str(e)}")]

    @mcp.tool()
    async def add_lab_annotation(
        lab_path: str,
        text_content: str,
        x: int = 50,
        y: int = 50,
    ) -> list[TextContent]:
        """
        Add a text annotation (label) to the lab canvas.

        Places a text label on the EVE-NG lab diagram at the
        specified canvas coordinates. Useful for documenting
        network segments, marking topology regions, or adding
        instructional notes to labs.
        Inspired by cml-mcp add_annotation_to_cml_lab.

        Args:
            lab_path: Full path to the lab (e.g., /my_lab.unl)
            text_content: The text to display (max 4096 chars)
            x: Horizontal position (percentage 0-100, default 50)
            y: Vertical position (percentage 0-100, default 50)
        """
        try:
            logger.info(f"Adding annotation to lab: {lab_path}")
            if not eveng_client.is_connected:
                return [TextContent(type="text", text="Not connected.")]

            payload = {
                "type": "text",
                "data": text_content,
                "x": x,
                "y": y,
            }

            result = await asyncio.to_thread(
                eveng_client.api.add_lab_object,
                lab_path,
                payload
            )

            return [TextContent(
                type="text",
                text=(
                    f"Annotation added to lab {lab_path}:\n"
                    f"  Text: \"{text_content}\"\n"
                    f"  Position: ({x}%, {y}%)\n\n"
                    f"Use get_lab_annotations to view all labels."
                )
            )]
        except Exception as e:
            logger.error(f"Failed to add annotation: {e}")
            return [TextContent(type="text", text=f"Failed to add annotation: {str(e)}")]

    @mcp.tool()
    async def delete_lab_annotation(
        lab_path: str,
        object_id: str,
    ) -> list[TextContent]:
        """
        Delete an annotation (label) from the lab canvas.

        Removes a specific annotation object from the EVE-NG
        lab diagram by its object ID.
        Inspired by cml-mcp delete_annotation_from_lab.

        WARNING: This action is irreversible.

        Args:
            lab_path: Full path to the lab
            object_id: The annotation object ID to delete
        """
        try:
            logger.info(f"Deleting annotation {object_id} from lab: {lab_path}")
            if not eveng_client.is_connected:
                return [TextContent(type="text", text="Not connected.")]

            result = await asyncio.to_thread(
                eveng_client.api.delete_lab_object,
                lab_path,
                object_id
            )

            return [TextContent(
                type="text",
                text=f"Annotation {object_id} deleted from lab {lab_path}."
            )]
        except Exception as e:
            logger.error(f"Failed to delete annotation: {e}")
            return [TextContent(type="text", text=f"Failed to delete annotation: {str(e)}")]
