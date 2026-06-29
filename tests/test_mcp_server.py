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

    def test_get_project_info_tool(self):
        mock_data = {
            "success": True,
            "project_filename": "test_project.pixem",
            "layers": [{"uuid": "123", "name": "Layer 1", "type": "image", "visible": True}],
        }

        def handle_info(future):
            future.set_result(mock_data)

        self.bridge.get_project_info_requested.connect(handle_info)

        result_future = Future()

        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # call_tool is a coroutine on FastMCP
                res = loop.run_until_complete(
                    self.server_thread.mcp.call_tool("get_project_info", arguments={})
                )
                result_future.set_result(res)
            except Exception as e:
                result_future.set_exception(e)
            finally:
                loop.close()

        t = threading.Thread(target=run_async)
        t.start()

        # Process Qt events on the main thread until the result is ready
        start_time = time.time()
        while not result_future.done():
            QCoreApplication.processEvents()
            time.sleep(0.01)
            if time.time() - start_time > 2.0:
                self.fail("Timeout waiting for tool call result")

        t.join()

        # Verify the result
        res = result_future.result()
        self.assertTrue(len(res[0]) > 0)
        self.assertIn("test_project.pixem", res[0][0].text)

    def test_set_layer_properties_tool(self):
        received_uuid = None
        received_props = None

        def handle_set_props(layer_uuid, props, future):
            nonlocal received_uuid, received_props
            received_uuid = layer_uuid
            received_props = props
            future.set_result({"success": True})

        self.bridge.set_layer_properties_requested.connect(handle_set_props)

        result_future = Future()

        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                res = loop.run_until_complete(
                    self.server_thread.mcp.call_tool(
                        "set_layer_properties",
                        arguments={
                            "layer_uuid": "layer-111",
                            "position_x": 10.5,
                            "position_y": 20.0,
                            "rotation": 90,
                            "visible": False,
                        },
                    )
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
                self.fail("Timeout waiting for tool call result")

        t.join()

        # Verify bridge received correct arguments
        self.assertEqual(received_uuid, "layer-111")
        self.assertEqual(received_props["position"], (10.5, 20.0))
        self.assertEqual(received_props["rotation"], 90)
        self.assertEqual(received_props["visible"], False)

        # Verify tool response
        res = result_future.result()
        self.assertTrue(len(res[0]) > 0)
        self.assertIn("success", res[0][0].text)


if __name__ == "__main__":
    unittest.main()
