from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
    QApplication,
    QSplitter,
    QPushButton,
    QStackedWidget,
    QFileDialog,
    QHBoxLayout,
    QLineEdit,
    QLabel,
)
from PySide6.QtCore import Qt, QDir


class DeleteWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)

        self.pages_widget = QWidget()
        self.pages_layout = QVBoxLayout(self.pages_widget)
        self.file_label = QLabel("File:")
        self.pages_list = QListWidget()
        self.pages_layout.addWidget(self.file_label, 0, Qt.AlignmentFlag.AlignCenter)
        self.pages_layout.addWidget(self.pages_list)

        self.controls_widget = QWidget()
        self.controls_layout = QHBoxLayout(self.controls_widget)
        self.add_file_btn = QPushButton("Add File")
        self.add_file_btn.clicked.connect(self.open_file)

        self.pages_input = QLineEdit()
        self.pages_input.setPlaceholderText("pages (i.e 1,3-5,4)")
        self.split_btn = QPushButton("Delete")
        self.pages_input.setEnabled(False)
        self.split_btn.setEnabled(False)

        self.pages_list.model().rowsInserted.connect(self.on_pages_change)
        self.pages_list.model().rowsRemoved.connect(self.on_pages_change)

        self.controls_layout.addWidget(self.add_file_btn)
        self.controls_layout.addStretch()
        self.controls_layout.addWidget(self.pages_input)
        self.controls_layout.addWidget(self.split_btn)

        self.layout.addWidget(self.pages_widget)
        self.layout.addStretch()
        self.layout.addWidget(self.controls_widget)

    def open_file(self):
        self.path, _ = QFileDialog.getOpenFileName(
            self, "Open File", QDir.homePath(), "PDFs (*.pdf)"
        )
        self.file_label.setText(f"File: {self.path}")

    def on_pages_change(self):
        self.pages_input.setEnabled(self.pages_list.count() > 0)
        self.split_btn.setEnabled(self.pages_list.count() > 0)
