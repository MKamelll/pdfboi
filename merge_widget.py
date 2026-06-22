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
    QProgressBar,
    QMessageBox,
)
from PySide6.QtCore import Qt, QDir, QThread, Signal
from pypdf import PdfWriter


class Worker(QThread):
    results_ready = Signal(PdfWriter)
    progress = Signal(int)
    total_ready = Signal(int)
    error = Signal(str)

    def __init__(self, files: list[str]):
        super().__init__()
        self.files = files

    def run(self) -> None:
        if len(self.files) < 1:
            self.error.emit("Files cannot be empty")

        self.total_ready.emit(len(self.files))

        merger = PdfWriter()

        for i, path in enumerate(self.files):
            merger.append(path)
            self.progress.emit(i + 1)

        self.results_ready.emit(merger)


class MergeWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._layout = QVBoxLayout(self)
        self.file_list = QListWidget()
        self.file_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()

        self.controls_widget = QWidget()
        self.controls_layout = QHBoxLayout(self.controls_widget)

        self.add_files_btn = QPushButton("Add Files")
        self.add_files_btn.clicked.connect(self.open_files)
        self.controls_layout.addWidget(self.add_files_btn)
        self.controls_layout.addStretch()
        self.merge_files_btn = QPushButton("Merge")
        self.merge_files_btn.setEnabled(False)
        self.merge_files_btn.clicked.connect(self.merge_files)
        self.controls_layout.addWidget(self.merge_files_btn)

        self.file_list.model().rowsInserted.connect(
            lambda _: self.merge_files_btn.setEnabled(self.file_list.count() > 0)
        )

        self.file_list.model().rowsRemoved.connect(
            lambda _: self.merge_files_btn.setEnabled(self.file_list.count() > 0)
        )

        self._layout.addWidget(self.file_list)
        self._layout.addStretch()
        self._layout.addWidget(self.progress_bar)
        self._layout.addWidget(self.controls_widget)

    def open_files(self) -> None:
        self.paths, _ = QFileDialog.getOpenFileNames(
            self, "Open Files", QDir.homePath(), "PDFs (*.pdf)"
        )

        self.file_list.addItems(self.paths)

    def merge_files(self) -> None:
        self.progress_bar.show()
        self.worker = Worker(
            [self.file_list.item(i).text() for i in range(self.file_list.count())]
        )
        self.worker.total_ready.connect(self.progress_bar.setMaximum)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.results_ready.connect(self.on_results)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_results(self, doc: PdfWriter) -> None:
        self.progress_bar.hide()
        self.progress_bar.reset()
        self.out_path, _ = QFileDialog.getSaveFileName(
            self, "Save as", QDir.homePath(), "PDFs (*.pdf)"
        )
        doc.write(self.out_path + ".pdf")

    def on_error(self, err: str) -> None:
        QMessageBox.warning(self, "Error", err)
