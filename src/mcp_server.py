# Pixem MCP Server
# Copyright 2026 - Ricardo Quesada

import asyncio
import json
import logging
from concurrent.futures import Future

from mcp.server.fastmcp import FastMCP
from PySide6.QtCore import QObject, QThread, Signal

logger = logging.getLogger(__name__)


class McpBridge(QObject):
    # Signals to request actions on the main thread
    get_project_info_requested = Signal(Future)
    get_layer_details_requested = Signal(str, Future)
    get_layer_image_requested = Signal(str, Future)
    get_partition_route_requested = Signal(str, str, Future)
    find_auto_path_requested = Signal(str, str, int, int, int, int, bool, bool, Future)
    add_layer_requested = Signal(dict, Future)
    delete_layer_requested = Signal(str, Future)
    duplicate_layer_requested = Signal(str, Future)
    fit_layer_to_hoop_requested = Signal(str, Future)
    set_layer_properties_requested = Signal(str, dict, Future)
    set_partition_route_requested = Signal(str, str, list, Future)
    delete_partition_requested = Signal(str, str, Future)
    update_layer_partitions_requested = Signal(str, list, Future)
    undo_requested = Signal(Future)
    redo_requested = Signal(Future)
    set_project_properties_requested = Signal(dict, Future)

    def __init__(self):
        super().__init__()

    async def _call_main_thread(self, signal: Signal, *args) -> any:
        future = Future()
        # Emit the signal. Qt will queue this connection across threads safely.
        signal.emit(*args, future)
        # Wait for the main thread to set the result
        return await asyncio.wrap_future(future)


class McpServerThread(QThread):
    def __init__(self, bridge: McpBridge, port: int = 8123):
        super().__init__()
        self.bridge = bridge
        self.port = port
        # Initialize FastMCP with the specified port
        self.mcp = FastMCP("Pixem", port=self.port)
        self._setup_tools()

    def _setup_tools(self):
        @self.mcp.tool()
        async def pixem_get_project_info() -> str:
            """Get general project status, hoop size, and list of layers."""
            try:
                res = await self.bridge._call_main_thread(self.bridge.get_project_info_requested)
                return json.dumps(res)
            except Exception as e:
                return json.dumps({"success": False, "error": str(e)})

        @self.mcp.tool()
        async def pixem_get_layer_details(layer_uuid: str) -> str:
            """Get detailed properties and partitions of a specific layer.

            Args:
                layer_uuid: The unique identifier (UUID) of the layer.
            """
            try:
                res = await self.bridge._call_main_thread(
                    self.bridge.get_layer_details_requested, layer_uuid
                )
                return json.dumps(res)
            except Exception as e:
                return json.dumps({"success": False, "error": str(e)})

        @self.mcp.tool()
        async def pixem_get_layer_image(layer_uuid: str) -> str:
            """Get the layer's image as a Base64-encoded PNG string.

            Args:
                layer_uuid: The unique identifier (UUID) of the layer.
            """
            try:
                res = await self.bridge._call_main_thread(
                    self.bridge.get_layer_image_requested, layer_uuid
                )
                return json.dumps(res)
            except Exception as e:
                return json.dumps({"success": False, "error": str(e)})

        @self.mcp.tool()
        async def pixem_get_partition_route(layer_uuid: str, partition_uuid: str) -> str:
            """Get the current route (ordered list of shapes) for a specific partition.

            Args:
                layer_uuid: The unique identifier (UUID) of the layer containing the partition.
                partition_uuid: The unique identifier (UUID) of the partition.
            """
            try:
                res = await self.bridge._call_main_thread(
                    self.bridge.get_partition_route_requested, layer_uuid, partition_uuid
                )
                return json.dumps(res)
            except Exception as e:
                return json.dumps({"success": False, "error": str(e)})

        @self.mcp.tool()
        async def pixem_find_auto_path(
            layer_uuid: str,
            partition_uuid: str,
            start_x: int,
            start_y: int,
            end_x: int,
            end_y: int,
            use_weights: bool = True,
            simplify: bool = True,
        ) -> str:
            """Find an optimal stitching path (sequence of points) between two pixels in a layer.

            This uses Pixem's internal pathfinding algorithm (which considers color distances to find
            the best path) and returns a list of points.

            Args:
                layer_uuid: The unique identifier (UUID) of the layer.
                partition_uuid: The unique identifier (UUID) of the partition.
                start_x: X coordinate of the start pixel.
                start_y: Y coordinate of the start pixel.
                end_x: X coordinate of the end pixel.
                end_y: Y coordinate of the end pixel.
                use_weights: If True, uses color distances as weights to find the best path.
                             If False, finds the path with the fewest segments.
                simplify: If True, simplifies the path by keeping only corner points (collinear reduction).
                          If False, returns all intermediate pixel vertices.
            """
            try:
                res = await self.bridge._call_main_thread(
                    self.bridge.find_auto_path_requested,
                    layer_uuid,
                    partition_uuid,
                    start_x,
                    start_y,
                    end_x,
                    end_y,
                    use_weights,
                    simplify,
                )
                return json.dumps(res)
            except Exception as e:
                return json.dumps({"success": False, "error": str(e)})

        @self.mcp.tool()
        async def pixem_add_layer(
            filepath: str = None, text: str = None, font_name: str = None, color_name: str = None
        ) -> str:
            """Add a new image or text layer. Provide filepath for image layer, or text/font_name/color_name for text layer.

            Args:
                filepath: Path to the image file (for image layers).
                text: Text content (for text layers).
                font_name: Name of the font to use (for text layers, defaults to 'Arial').
                color_name: Hex color code, e.g., '#RRGGBB' (for text layers, defaults to black '#000000').
            """
            try:
                args = {
                    "filepath": filepath,
                    "text": text,
                    "font_name": font_name,
                    "color_name": color_name,
                }
                res = await self.bridge._call_main_thread(self.bridge.add_layer_requested, args)
                return json.dumps(res)
            except Exception as e:
                return json.dumps({"success": False, "error": str(e)})

        @self.mcp.tool()
        async def pixem_delete_layer(layer_uuid: str) -> str:
            """Delete an existing layer.

            Args:
                layer_uuid: The unique identifier (UUID) of the layer to delete.
            """
            try:
                res = await self.bridge._call_main_thread(
                    self.bridge.delete_layer_requested, layer_uuid
                )
                return json.dumps(res)
            except Exception as e:
                return json.dumps({"success": False, "error": str(e)})

        @self.mcp.tool()
        async def pixem_duplicate_layer(layer_uuid: str) -> str:
            """Duplicate an existing layer.

            Args:
                layer_uuid: The unique identifier (UUID) of the layer to duplicate.
            """
            try:
                res = await self.bridge._call_main_thread(
                    self.bridge.duplicate_layer_requested, layer_uuid
                )
                return json.dumps(res)
            except Exception as e:
                return json.dumps({"success": False, "error": str(e)})

        @self.mcp.tool()
        async def pixem_fit_layer_to_hoop(layer_uuid: str) -> str:
            """Fit a layer to the hoop size.

            Args:
                layer_uuid: The unique identifier (UUID) of the layer.
            """
            try:
                res = await self.bridge._call_main_thread(
                    self.bridge.fit_layer_to_hoop_requested, layer_uuid
                )
                return json.dumps(res)
            except Exception as e:
                return json.dumps({"success": False, "error": str(e)})

        @self.mcp.tool()
        async def pixem_set_layer_properties(
            layer_uuid: str,
            position_x: float = None,
            position_y: float = None,
            rotation: int = None,
            opacity: float = None,
            visible: bool = None,
            name: str = None,
            pixel_size_x: float = None,
            pixel_size_y: float = None,
            pixel_aspect_ratio_mode: str = None,
        ) -> str:
            """Update properties of a layer.

            Args:
                layer_uuid: The unique identifier (UUID) of the layer to update.
                position_x: New X position in millimeters.
                position_y: New Y position in millimeters.
                rotation: New rotation angle in degrees (0 to 359).
                opacity: New opacity value (0.0 for transparent to 1.0 for opaque).
                visible: New visibility state.
                name: New name of the layer.
                pixel_size_x: New pixel width in millimeters.
                pixel_size_y: New pixel height in millimeters.
                pixel_aspect_ratio_mode: New pixel aspect ratio mode (e.g. 'square', 'ignore', or 'preserve').
            """
            try:
                props = {}
                if position_x is not None and position_y is not None:
                    props["position"] = (position_x, position_y)
                if rotation is not None:
                    props["rotation"] = rotation
                if opacity is not None:
                    props["opacity"] = opacity
                if visible is not None:
                    props["visible"] = visible
                if name is not None:
                    props["name"] = name
                if pixel_size_x is not None and pixel_size_y is not None:
                    props["pixel_size"] = (pixel_size_x, pixel_size_y)
                if pixel_aspect_ratio_mode is not None:
                    props["pixel_aspect_ratio_mode"] = pixel_aspect_ratio_mode

                res = await self.bridge._call_main_thread(
                    self.bridge.set_layer_properties_requested, layer_uuid, props
                )
                return json.dumps(res)
            except Exception as e:
                return json.dumps({"success": False, "error": str(e)})

        @self.mcp.tool()
        async def pixem_set_partition_route(
            layer_uuid: str, partition_uuid: str, route_json: str
        ) -> str:
            """Replace the entire route (list of shapes) of a partition.

            Args:
                layer_uuid: The unique identifier (UUID) of the layer containing the partition.
                partition_uuid: The unique identifier (UUID) of the partition.
                route_json: A JSON string representing a list of shapes. Each shape should have a 'type' ('rect' or 'path').
                           Example: '[{"type": "rect", "x": 10, "y": 12}, {"type": "path", "points": [{"x": 0, "y": 0}, {"x": 5, "y": 5}]}]'
            """
            try:
                route = json.loads(route_json)
                res = await self.bridge._call_main_thread(
                    self.bridge.set_partition_route_requested, layer_uuid, partition_uuid, route
                )
                return json.dumps(res)
            except Exception as e:
                return json.dumps({"success": False, "error": str(e)})

        @self.mcp.tool()
        async def pixem_delete_partition(layer_uuid: str, partition_uuid: str) -> str:
            """Delete a partition from a layer.

            Args:
                layer_uuid: The unique identifier (UUID) of the layer containing the partition.
                partition_uuid: The unique identifier (UUID) of the partition to delete.
            """
            try:
                res = await self.bridge._call_main_thread(
                    self.bridge.delete_partition_requested, layer_uuid, partition_uuid
                )
                return json.dumps(res)
            except Exception as e:
                return json.dumps({"success": False, "error": str(e)})

        @self.mcp.tool()
        async def pixem_update_layer_partitions(layer_uuid: str, partition_uuids: list[str]) -> str:
            """Reorder or update the partitions of a layer.

            Args:
                layer_uuid: The unique identifier (UUID) of the layer.
                partition_uuids: An ordered list of partition UUIDs representing the new sequence.
            """
            try:
                res = await self.bridge._call_main_thread(
                    self.bridge.update_layer_partitions_requested, layer_uuid, partition_uuids
                )
                return json.dumps(res)
            except Exception as e:
                return json.dumps({"success": False, "error": str(e)})

        @self.mcp.tool()
        async def pixem_undo() -> str:
            """Undo the last action on the main undo stack."""
            try:
                res = await self.bridge._call_main_thread(self.bridge.undo_requested)
                return json.dumps(res)
            except Exception as e:
                return json.dumps({"success": False, "error": str(e)})

        @self.mcp.tool()
        async def pixem_redo() -> str:
            """Redo the last undone action on the main undo stack."""
            try:
                res = await self.bridge._call_main_thread(self.bridge.redo_requested)
                return json.dumps(res)
            except Exception as e:
                return json.dumps({"success": False, "error": str(e)})

        @self.mcp.tool()
        async def pixem_set_project_properties(
            hoop_size_x: float = None,
            hoop_size_y: float = None,
            hoop_visible: bool = None,
            hoop_color: str = None,
            canvas_background_color: str = None,
            partition_foreground_color: str = None,
            partition_background_color: str = None,
            zoom_factor: float = None,
        ) -> str:
            """Set project-wide properties.

            Args:
                hoop_size_x: New hoop width in millimeters.
                hoop_size_y: New hoop height in millimeters.
                hoop_visible: Whether the embroidery hoop should be visible.
                hoop_color: Hex color code for the hoop boundary.
                canvas_background_color: Hex color code for the main canvas background.
                partition_foreground_color: Hex color code for the partition foreground color.
                partition_background_color: Hex color code for the partition background color.
                zoom_factor: New canvas zoom factor (e.g. 1.0 for 100%).
            """
            try:
                props = {}
                if hoop_size_x is not None and hoop_size_y is not None:
                    props["hoop_size"] = (hoop_size_x, hoop_size_y)
                if hoop_visible is not None:
                    props["hoop_visible"] = hoop_visible
                if hoop_color is not None:
                    props["hoop_color"] = hoop_color
                if canvas_background_color is not None:
                    props["canvas_background_color"] = canvas_background_color
                if partition_foreground_color is not None:
                    props["partition_foreground_color"] = partition_foreground_color
                if partition_background_color is not None:
                    props["partition_background_color"] = partition_background_color
                if zoom_factor is not None:
                    props["zoom_factor"] = zoom_factor

                res = await self.bridge._call_main_thread(
                    self.bridge.set_project_properties_requested, props
                )
                return json.dumps(res)
            except Exception as e:
                return json.dumps({"success": False, "error": str(e)})

    def run(self):
        logger.info(f"Starting MCP Server on port {self.port} using SSE...")
        self.mcp.run(transport="sse")
