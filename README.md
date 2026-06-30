# Pixem

**Pixem** is a pixel-art to machine-embroidery application. It allows you to transform pixel-based designs into embroidery patterns, bridging the gap between digital art and physical textiles.

![Pixem Logo](src/res/logo512.png)

## Features

- **Pixel-Art Conversion**: Seamlessly convert pixel-art designs into embroidery paths.
- **Interactive Canvas Transformations**: Scale, rotate, and mirror layers directly on the canvas using interactive handles or quick keyboard shortcuts.
- **Layer Management**: Organize your design into multiple layers for better control.
- **Undo/Redo Support**: Full command-based undo/redo system for all actions.
- **Export Options**: Export your designs to SVG and PNG formats (with more to come).
- **Machine Embroidery Focused**: Features like "Fit to Hoop" ensure your designs are ready for production.
- **Cross-Platform**: Built with Python and PySide6, designed to run on macOS, Windows, and Linux.

## Requirements

- Python 3.10 or newer
- PySide6

## Getting Started

### Installation

1. Clone the repository:
   ```shell
   git clone https://github.com/ricardoquesada/pixem.git
   cd pixem
   ```

2. Create and activate a virtual environment:
   ```shell
   make venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```shell
   pip install -r requirements.txt
   ```

### Running the Application

To start Pixem, run:
```shell
make run
```

Or directly via python:
```shell
python src/main.py
```

### Command Line Options

You can pass arguments to the startup script to open files or enable developer features:

```shell
# Open a specific project or image on startup
python src/main.py path/to/file.toml

# Start the application with the Model Context Protocol (MCP) Server enabled (default port 8123)
python src/main.py --mcp

# Start the MCP Server on a custom port
python src/main.py --mcp --mcp-port 9000
```

## Development

### Pre-commit Hooks

We use `pre-commit` to ensure code quality. Install it with:
```shell
pre-commit install
```

To update hooks:
```shell
pre-commit autoupdate
```

### Running Tests

```shell
make tests
```

## License

Pixem is licensed under the Apache License, Version 2.0. See the [LICENSE](LICENSE) file for more details.

## Authors

See the [AUTHORS](AUTHORS) file for a list of contributors.

---
Copyright (c) 2025-2026 Ricardo Quesada - [retro.moe](https://retro.moe)
