# Pixem
# Copyright 2026 - Ricardo Quesada

import asyncio
import os
import sys
import threading
import time
import unittest
from concurrent.futures import Future

# Ensure src is in path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from PySide6.QtCore import QCoreApplication

from mcp_server import McpBridge, McpServerThread


class TestMcpServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create QCoreApplication instance if it doesn't exist
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self):
        self.bridge = McpBridge()
        # Use a test port
        self.port = 8125
        self.server_thread = McpServerThread(self.bridge, port=self.port)

    def tearDown(self):
        pass

    def _run_tool_with_loop(self, tool_name, arguments=None):
        """Helper to run a tool call in a background thread and pump Qt events on the main thread."""
        if arguments is None:
            arguments = {}
        result_future = Future()

        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                res = loop.run_until_complete(
                    self.server_thread.mcp.call_tool(tool_name, arguments=arguments)
                )
                result_future.set_result(res)
            except Exception as e:
                result_future.set_exception(e)
            finally:
                loop.close()

        t = threading.Thread(target=run_async)
        t.start()

        start_time = time.time()
        while not result_future.done():
            QCoreApplication.processEvents()
            time.sleep(0.01)
            if time.time() - start_time > 2.0:
                self.fail(f"Timeout waiting for tool '{tool_name}' result")

        t.join()
        return result_future.result()

    def test_get_project_info_tool(self):
        mock_data = {
            "success": True,
            "project_filename": "test_project.pixem",
            "layers": [{"uuid": "123", "name": "Layer 1", "type": "image", "visible": True}],
        }
        self.bridge.get_project_info_requested.connect(lambda fut: fut.set_result(mock_data))

        res = self._run_tool_with_loop("get_project_info")
        self.assertTrue(len(res[0]) > 0)
        self.assertIn("test_project.pixem", res[0][0].text)

    def test_get_layer_details_tool(self):
        received_uuid = None

        def handle_details(layer_uuid, future):
            nonlocal received_uuid
            received_uuid = layer_uuid
            future.set_result(
                {
                    "success": True,
                    "uuid": layer_uuid,
                    "partitions": [{"uuid": "p1", "name": "P1", "color": "#ff0000"}],
                }
            )

        self.bridge.get_layer_details_requested.connect(handle_details)

        res = self._run_tool_with_loop("get_layer_details", {"layer_uuid": "layer-123"})
        self.assertEqual(received_uuid, "layer-123")
        self.assertTrue(len(res[0]) > 0)
        self.assertIn("layer-123", res[0][0].text)
        self.assertIn("#ff0000", res[0][0].text)

    def test_get_layer_image_tool(self):
        received_layer_uuid = None

        def handle_get_image(layer_uuid, future):
            nonlocal received_layer_uuid
            received_layer_uuid = layer_uuid
            future.set_result(
                {
                    "success": True,
                    "image_base64": "fake_base64_data",
                    "width": 10,
                    "height": 20,
                }
            )

        self.bridge.get_layer_image_requested.connect(handle_get_image)

        res = self._run_tool_with_loop("get_layer_image", {"layer_uuid": "layer-1"})
        self.assertEqual(received_layer_uuid, "layer-1")
        self.assertTrue(len(res[0]) > 0)
        self.assertIn("image_base64", res[0][0].text)
        self.assertIn("fake_base64_data", res[0][0].text)

    def test_get_partition_route_tool(self):
        received_layer_uuid = None
        received_partition_uuid = None

        def handle_get_route(layer_uuid, partition_uuid, future):
            nonlocal received_layer_uuid, received_partition_uuid
            received_layer_uuid = layer_uuid
            received_partition_uuid = partition_uuid
            future.set_result(
                {
                    "success": True,
                    "shapes": [{"type": "rect", "x": 5, "y": 6}],
                }
            )

        self.bridge.get_partition_route_requested.connect(handle_get_route)

        res = self._run_tool_with_loop(
            "get_partition_route", {"layer_uuid": "layer-1", "partition_uuid": "part-2"}
        )
        self.assertEqual(received_layer_uuid, "layer-1")
        self.assertEqual(received_partition_uuid, "part-2")
        self.assertTrue(len(res[0]) > 0)
        self.assertIn("shapes", res[0][0].text)
        self.assertIn("rect", res[0][0].text)

    def test_add_layer_tool(self):
        received_args = None

        def handle_add(args, future):
            nonlocal received_args
            received_args = args
            future.set_result({"success": True, "layer_uuid": "new-layer-uuid"})

        self.bridge.add_layer_requested.connect(handle_add)

        res = self._run_tool_with_loop(
            "add_layer",
            {
                "filepath": "image.png",
                "text": "hello",
                "font_name": "Arial",
                "color_name": "#ff0000",
            },
        )
        self.assertEqual(received_args["filepath"], "image.png")
        self.assertEqual(received_args["text"], "hello")
        self.assertTrue(len(res[0]) > 0)
        self.assertIn("new-layer-uuid", res[0][0].text)

    def test_delete_layer_tool(self):
        received_uuid = None

        def handle_delete(layer_uuid, future):
            nonlocal received_uuid
            received_uuid = layer_uuid
            future.set_result({"success": True})

        self.bridge.delete_layer_requested.connect(handle_delete)

        res = self._run_tool_with_loop("delete_layer", {"layer_uuid": "layer-to-delete"})
        self.assertEqual(received_uuid, "layer-to-delete")
        self.assertIn("true", res[0][0].text)

    def test_duplicate_layer_tool(self):
        received_uuid = None

        def handle_duplicate(layer_uuid, future):
            nonlocal received_uuid
            received_uuid = layer_uuid
            future.set_result({"success": True, "layer_uuid": "duplicate-uuid"})

        self.bridge.duplicate_layer_requested.connect(handle_duplicate)

        res = self._run_tool_with_loop("duplicate_layer", {"layer_uuid": "layer-to-dup"})
        self.assertEqual(received_uuid, "layer-to-dup")
        self.assertIn("duplicate-uuid", res[0][0].text)

    def test_fit_layer_to_hoop_tool(self):
        received_uuid = None

        def handle_fit(layer_uuid, future):
            nonlocal received_uuid
            received_uuid = layer_uuid
            future.set_result({"success": True})

        self.bridge.fit_layer_to_hoop_requested.connect(handle_fit)

        res = self._run_tool_with_loop("fit_layer_to_hoop", {"layer_uuid": "layer-to-fit"})
        self.assertEqual(received_uuid, "layer-to-fit")
        self.assertIn("true", res[0][0].text)

    def test_set_layer_properties_tool(self):
        received_uuid = None
        received_props = None

        def handle_set_props(layer_uuid, props, future):
            nonlocal received_uuid, received_props
            received_uuid = layer_uuid
            received_props = props
            future.set_result({"success": True})

        self.bridge.set_layer_properties_requested.connect(handle_set_props)

        res = self._run_tool_with_loop(
            "set_layer_properties",
            arguments={
                "layer_uuid": "layer-111",
                "position_x": 10.5,
                "position_y": 20.0,
                "rotation": 90,
                "visible": False,
            },
        )
        self.assertEqual(received_uuid, "layer-111")
        self.assertEqual(received_props["position"], (10.5, 20.0))
        self.assertEqual(received_props["rotation"], 90)
        self.assertEqual(received_props["visible"], False)
        self.assertTrue(len(res[0]) > 0)
        self.assertIn("success", res[0][0].text)

    def test_set_partition_route_tool(self):
        received_layer_uuid = None
        received_partition_uuid = None
        received_route = None

        def handle_set_route(layer_uuid, partition_uuid, route, future):
            nonlocal received_layer_uuid, received_partition_uuid, received_route
            received_layer_uuid = layer_uuid
            received_partition_uuid = partition_uuid
            received_route = route
            future.set_result({"success": True})

        self.bridge.set_partition_route_requested.connect(handle_set_route)

        res = self._run_tool_with_loop(
            "set_partition_route",
            {
                "layer_uuid": "layer-1",
                "partition_uuid": "part-2",
                "route_json": '[{"type": "rect", "x": 1, "y": 2}]',
            },
        )
        self.assertEqual(received_layer_uuid, "layer-1")
        self.assertEqual(received_partition_uuid, "part-2")
        self.assertEqual(len(received_route), 1)
        self.assertEqual(received_route[0]["type"], "rect")
        self.assertEqual(received_route[0]["x"], 1)
        self.assertEqual(received_route[0]["y"], 2)
        self.assertIn("true", res[0][0].text)

    def test_delete_partition_tool(self):
        received_layer_uuid = None
        received_partition_uuid = None

        def handle_delete_part(layer_uuid, partition_uuid, future):
            nonlocal received_layer_uuid, received_partition_uuid
            received_layer_uuid = layer_uuid
            received_partition_uuid = partition_uuid
            future.set_result({"success": True})

        self.bridge.delete_partition_requested.connect(handle_delete_part)

        res = self._run_tool_with_loop(
            "delete_partition", {"layer_uuid": "layer-1", "partition_uuid": "part-2"}
        )
        self.assertEqual(received_layer_uuid, "layer-1")
        self.assertEqual(received_partition_uuid, "part-2")
        self.assertIn("true", res[0][0].text)

    def test_update_layer_partitions_tool(self):
        received_layer_uuid = None
        received_partition_uuids = None

        def handle_update_parts(layer_uuid, partition_uuids, future):
            nonlocal received_layer_uuid, received_partition_uuids
            received_layer_uuid = layer_uuid
            received_partition_uuids = partition_uuids
            future.set_result({"success": True})

        self.bridge.update_layer_partitions_requested.connect(handle_update_parts)

        res = self._run_tool_with_loop(
            "update_layer_partitions",
            {"layer_uuid": "layer-1", "partition_uuids": ["part-2", "part-3"]},
        )
        self.assertEqual(received_layer_uuid, "layer-1")
        self.assertEqual(received_partition_uuids, ["part-2", "part-3"])
        self.assertIn("true", res[0][0].text)

    def test_undo_redo_tools(self):
        undo_called = False
        redo_called = False

        def handle_undo(future):
            nonlocal undo_called
            undo_called = True
            future.set_result({"success": True})

        def handle_redo(future):
            nonlocal redo_called
            redo_called = True
            future.set_result({"success": True})

        self.bridge.undo_requested.connect(handle_undo)
        self.bridge.redo_requested.connect(handle_redo)

        res_undo = self._run_tool_with_loop("undo")
        res_redo = self._run_tool_with_loop("redo")

        self.assertTrue(undo_called)
        self.assertTrue(redo_called)
        self.assertIn("true", res_undo[0][0].text)
        self.assertIn("true", res_redo[0][0].text)

    def test_set_project_properties_tool(self):
        received_props = None

        def handle_set_project_props(props, future):
            nonlocal received_props
            received_props = props
            future.set_result({"success": True})

        self.bridge.set_project_properties_requested.connect(handle_set_project_props)

        res = self._run_tool_with_loop(
            "set_project_properties",
            {
                "hoop_size_x": 100.0,
                "hoop_size_y": 150.0,
                "hoop_visible": True,
                "hoop_color": "#ffffff",
                "canvas_background_color": "#000000",
                "zoom_factor": 2.0,
            },
        )
        self.assertEqual(received_props["hoop_size"], (100.0, 150.0))
        self.assertEqual(received_props["hoop_visible"], True)
        self.assertEqual(received_props["hoop_color"], "#ffffff")
        self.assertEqual(received_props["canvas_background_color"], "#000000")
        self.assertEqual(received_props["zoom_factor"], 2.0)
        self.assertIn("true", res[0][0].text)


if __name__ == "__main__":
    unittest.main()
