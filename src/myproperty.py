# This Python file uses the following encoding: utf-8

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QVBoxLayout,
    QWidget,
    QLineEdit,
    QLabel,
    QPushButton,
    QColorDialog,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
)


class MyProperty:
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __str__(self):
        return f"{self.name}: {self.value}"


class PropertyEditor(QWidget):
    valueChanged = Signal(object)  # Signal to emit when the value changes

    def __init__(self, property):
        super().__init__()

        self.property = property
        self.editor = None

        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"{property.name}:"))

        if isinstance(property.value, str):
            self.editor = QLineEdit()
            self.editor.setText(property.value)
            self.editor.textChanged.connect(self.on_value_changed)
        elif isinstance(property.value, bool):
            # Implement boolean editor (e.g., QCheckBox)
            self.editor = QCheckBox()
        elif isinstance(property.value, int):
            # Implement integer editor (e.g., QSpinBox)
            self.editor = QSpinBox()
        elif isinstance(property.value, float):
            # Implement float editor (e.g., QDoubleSpinBox)
            self.editor = QDoubleSpinBox()
        elif isinstance(property.value, QColor):
            self.editor = QPushButton()
            self.editor.setStyleSheet(f"background-color: {property.value.name()}")
            self.editor.clicked.connect(self.show_color_dialog)
        else:
            self.editor = QLineEdit()
            self.editor.setText(str(property.value))
            self.editor.textChanged.connect(self.on_value_changed)

        if self.editor is not None:
            layout.addWidget(self.editor)
        self.setLayout(layout)

    def on_value_changed(self, text):
        try:
            # Convert the edited text to the appropriate data type
            if isinstance(self.property.value, str):
                self.property.value = text
            elif isinstance(self.property.value, int):
                self.property.value = int(text)
            elif isinstance(self.property.value, float):
                self.property.value = float(text)
            # ... handle other data types ...

            self.valueChanged.emit(self.property)
        except ValueError as e:
            print(f"Invalid input: {e}")

    def show_color_dialog(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.property.value = color
            self.editor.setStyleSheet(f"background-color: {color.name()}")
            self.valueChanged.emit(self.property)


if __name__ == "__main__":
    app = QApplication([])

    properties = [
        MyProperty("Name", "John Doe"),
        MyProperty("Age", 30),
        MyProperty("Color", QColor("red")),
        MyProperty("Enabled", False),
        MyProperty("Pi", 3.14),
    ]

    window = QWidget()
    layout = QVBoxLayout(window)

    for property in properties:
        editor = PropertyEditor(property)
        editor.valueChanged.connect(
            lambda prop: print(f"{prop.name}: {prop.value}")
        )  # Example: Print changes
        layout.addWidget(editor)

    window.show()
    app.exec()
