---
name: optimize-stitch-route
description: Optimizes the embroidery stitching route of partitions in Pixem layers.
---

# Optimizing Embroidery Stitching Route in Pixem

This skill guides you through the process of optimizing the embroidery stitching route (path planning) for all partitions in the currently open Pixem project. The goal is to create a continuous, efficient path that minimizes jump stitches and avoids crossing unrelated colors.

## Workflow

### Step 1: Get Project and Layer Details
1. Call `get_project_info` to get the list of layers in the active project.
2. For each layer:
   * Call `get_layer_details(layer_uuid)` to retrieve the list of partitions, their UUIDs, and colors.
   * Call `get_layer_image(layer_uuid)` to fetch the base64-encoded PNG image of the layer.

### Step 2: Analyze the Layer Image & Partitions
1. Decode the base64 PNG image returned by `get_layer_image`.
2. Map out the pixels belonging to each partition (each partition is defined by a unique color).
3. Identify the connected components (clusters of pixels of the same color) for each partition.

### Step 3: Plan the Route for Each Partition
For each partition:
1. Retrieve the current route by calling `get_partition_route(layer_uuid, partition_uuid)`.
2. Plan an optimized route (an ordered list of shapes) that visits all pixels of the partition's color.
3. **Traversal within a component**:
   * Order the pixels (`rect` shapes) in a continuous sequence (e.g., using a snake-like traversal or nearest-neighbor) to minimize stitching distance.
4. **Connecting disconnected components**:
   * To connect two disconnected clusters of the same color, do not use a straight line that crosses other colors.
   * Instead, use the **`find_auto_path`** tool:
     ```json
     find_auto_path(
       layer_uuid="...",
       partition_uuid="...",
       start_x=exit_x,
       start_y=exit_y,
       end_x=entry_x,
       end_y=entry_y,
       use_weights=true,
       simplify=true
     )
     ```
     This tool returns a list of points representing the optimal path that minimizes color distance (i.e., hugs the same or similar colors).
   * Convert the returned points into a `path` shape:
     ```json
     {
       "type": "path",
       "points": [{"x": x1, "y": y1}, {"x": x2, "y": y2}, ...]
     }
     ```
5. **Construct the final route**:
   * Combine the pixel `rect` shapes and the connecting `path` shapes into a single ordered list.
   * Example route JSON:
     ```json
     [
       {"type": "rect", "x": 10, "y": 10},
       {"type": "rect", "x": 11, "y": 10},
       {
         "type": "path",
         "points": [{"x": 11, "y": 10}, {"x": 12, "y": 11}, {"x": 15, "y": 11}]
       },
       {"type": "rect", "x": 15, "y": 11},
       {"type": "rect", "x": 16, "y": 11}
     ]
     ```

### Step 4: Apply the Optimized Route
1. Call **`set_partition_route(layer_uuid, partition_uuid, route_json)`** to update the partition's route in Pixem.
2. Verify that the tool returns `{"success": true}`. The changes will immediately reflect in the Pixem UI and the undo stack.
