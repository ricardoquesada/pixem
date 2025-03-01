# Pixem
# Copyright 2025 - Ricardo Quesada

from PySide6.QtGui import QImage, QUndoCommand

from main_window import MainWindow


class DrawCommand(QUndoCommand):
    def __init__(self, editor: MainWindow, old_image: QImage) -> None:
        super().__init__()
        self.editor = editor
        self.old_image = old_image
        self.new_image = editor.state.current_layer.image.copy()

    def undo(self) -> None:
        self.editor.state.current_layer.image = self.old_image
        self.editor.update()

    def redo(self) -> None:
        self.editor.state.current_layer.image = self.new_image
        self.editor.update()
