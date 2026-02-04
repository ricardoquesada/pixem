# AGENTS.md

This file provides an overview of the Pixem codebase for AI agents and developers.

## Project Overview

**Pixem** is a pixel-art to machine-embroidery application tailored for transforming pixel-based designs into embroidery patterns. It is a cross-platform desktop application built with **Python 3.10+** and **PySide6** (Qt for Python).

## Tech Stack

- **Language**: Python 3.10+
- **GUI Framework**: PySide6 (Qt)
- **Core Libraries**:
  - `numpy`, `pillow`: Image processing
  - `networkx`: Graph algorithms (likely for stitching paths)
  - `matplotlib`: Visualization/Math
  - `coloraide`: Color manipulation
- **Build System**: Makefile, `pip`
- **Packaging**: `pyinstaller`
- **Testing**: standard `unittest` (in `tests/` directory)
- **Linting/Formatting**:
  - `black`: Code formatting
  - `isort`: Import sorting
  - `ruff`: Fast Python linter
  - Configured via `.pre-commit-config.yaml`

## Directory Structure

```
pixem/
├── src/                # Main source code
│   ├── main.py         # Application entry point
│   ├── main_window.py  # Main application window and UI coordination
│   ├── state.py        # Central state management (Data & Undo Stack)
│   ├── layer.py        # Layer data models (ImageLayer, TextLayer)
│   ├── canvas.py       # Custom widget for rendering the workspace
│   ├── undo_commands.py # Command implementations for Undo/Redo
│   ├── ...             # Other modules (dialogs, utilities, parsers)
│   └── res/            # Resources (compiled Qt resources, icons)
├── tests/              # Unit tests
├── .github/            # GitHub Actions workflows
├── resources/          # Raw non-compiled resources (icons, translations)
├── requirements.txt    # Python dependencies
├── Makefile            # Convenience commands
└── README.md           # User facing documentation
```

## Architecture

Pixem follows a structure that separates **State** (Data), **Logic**, and **UI**.

### 1. State Management (`src/state.py`)
- The `State` class acts as the single source of truth for the open project.
- It manages:
  - **Layers**: A collection of `Layer` objects loaded from files or created.
  - **Properties**: Global project settings (Hoop size, colors, zoom).
  - **Undo Stack**: A `QUndoStack` that records all modification commands.
- It uses **PySide6 Signals** (e.g., `layer_added`, `property_changed`) to notify the UI of any state mutations.

### 2. Layers System (`src/layer.py`)
- The core data unit is the `Layer`.
- Layers can be:
  - `ImageLayer`: Based on a bitmap image.
  - `TextLayer`: Generated from text input.
- Layers contain **Partitions** (logic for pixel-to-stitch conversion regions) and **Properties** (position, rotation, etc.).
- `EmbeddingParameters` class handles machine-embroidery specific info.

### 3. Undo/Redo System (`src/undo_commands.py`)
- All state-modifying actions are encapsulated in `QUndoCommand` subclasses.
- The `State` class methods (like `add_layer`, `update_layer_properties`) push these commands onto the global `undo_stack`.

### 4. UI Layer
- `MainWindow` (`src/main_window.py`) orchestrates the application views and connects Signal/Slots.
- `Canvas` (`src/canvas.py`) is the custom painting widget responsible for rendering layers and handling direct mouse interactions.

## Coding Conventions

- **Type Hinting**: All logic code uses Python type hints extensively.
- **Logging**: The project uses the standard `logging` module.
- **Imports**: standard library -> third party -> local application imports.
- **Resources**: Assets are compiled into Python files (e.g., `rc_resources.py`).

## Common Tasks

### Adding a new feature
1.  **Define Data**: If it requires new data, update `Layer`, `LayerProperties`, or `State`.
2.  **Define Command**: Create a new `QUndoCommand` in `src/undo_commands.py` to handle the mutation.
3.  **Update State**: Add a method in `State` to push this command.
4.  **Update UI**: Implement the trigger in `MainWindow` or a Dialog, calling the method on `State`.

### Running Tests
Use the Makefile:
```bash
make tests
```

### Running the App
```bash
make run
# or
python src/main.py
```

### Resource Management
- **Compile Resources** (`.qrc` -> `.py`):
  ```bash
  make resources
  ```
- **Update Translations**:
  ```bash
  make lupdate   # Extract strings
  make lrelease  # Compile translations
  ```
- **Build Distributable** (via PyInstaller):
  ```bash
  make dist
  ```
