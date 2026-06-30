# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v0.2.0] - 2026-06-30

### Added
- Model Context Protocol (MCP) server support with thread-safe bridge, enabling external AI agent interaction (exposed tools: `find_auto_path`, `set_partition_route`, `get_partition_route`, etc.).
- Interactive canvas handles for scaling, rotating, and mirroring layers.
- Canvas grid and snapping functionality.
- Tab-level unsaved change (dirty) indicators.
- Pixel Editor Dialog for editing individual layer pixels.
- Support for opening project or image files directly from the command line.
- Local undo/redo stack for the partition editor and keyboard shortcuts for actions in the edit partition view.
- Background worker thread offloading for image layer partition processing to keep the UI responsive.
- Documentation for `optimize-stitch-route` agent skill.
- Unit tests for the command-line interface, canvas snapping, Pixel Editor, and MCP server.

### Changed
- Extracted layer hit testing logic to helper methods to deduplicate mouse events.
- Renamed partition "path" property and related methods to "route".

## [v0.1.5] - 2026-02-05

Initial public release
