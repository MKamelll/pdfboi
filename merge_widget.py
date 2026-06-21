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
)
from PySide6.QtCore import Qt, QDir


class MergeWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.file_list = QListWidget()
        self.file_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)

        self.controls_widget = QWidget()
        self.controls_layout = QHBoxLayout(self.controls_widget)

        self.add_files_btn = QPushButton("Add Files")
        self.add_files_btn.clicked.connect(self.open_files)
        self.controls_layout.addWidget(self.add_files_btn)
        self.controls_layout.addStretch()
        self.merge_files_btn = QPushButton("Merge")
        self.merge_files_btn.setEnabled(False)
        self.controls_layout.addWidget(self.merge_files_btn)

        self.file_list.model().rowsInserted.connect(
            lambda _: self.merge_files_btn.setEnabled(self.file_list.count() > 0)
        )

        self.file_list.model().rowsRemoved.connect(
            lambda _: self.merge_files_btn.setEnabled(self.file_list.count() > 0)
        )

        self.layout.addWidget(self.file_list)
        self.layout.addStretch()
        self.layout.addWidget(self.controls_widget)

    def open_files(self):
        self.paths, _ = QFileDialog.getOpenFileNames(
            self, "Open Files", QDir.homePath(), "PDFs (*.pdf)"
        )

        self.file_list.addItems(self.paths)
