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
    QProgressBar,
    QListWidgetItem,
    QSizePolicy,
    QMessageBox,
)
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt, QDir, QThread, Signal, QSize
from pdflist_widget import PdfListWidget
from thumbnailwidget import ThumbnailWidget, ThumbnailWorker
from pypdf import PdfWriter, PdfReader
import pypdfium2 as pypdfium

from util import calculate_indices


class Worker(QThread):
    results_ready = Signal(PdfWriter)
    progress = Signal(int)
    total_ready = Signal(int)
    error = Signal(str)
    done = Signal()

    def __init__(self, path: str, indices: list[int]):
        super().__init__()
        self.path = path
        self.indices = indices

    def run(self) -> None:
        src_doc = PdfReader(self.path)
        out_doc = PdfWriter()
        self.total_ready.emit(len(self.indices))

        for i, index in enumerate(self.indices):
            out_doc.append(src_doc, [index])
            self.progress.emit(i + 1)

        self.results_ready.emit(out_doc)
        self.done.emit()


class SplitWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._layout = QVBoxLayout(self)
        self.path: str | None = None
        self.indices: list[int] | None = None
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()

        self.file_label = QLabel("File:")
        self.list_widget = PdfListWidget()
        self.list_widget.started.connect(self.progress_bar.show)
        self.list_widget.progress_max.connect(self.progress_bar.setMaximum)
        self.list_widget.progress_update.connect(self.progress_bar.setValue)
        self.list_widget.done.connect(self.progress_bar.hide)
        self.list_widget.done.connect(self.progress_bar.reset)
        self.list_widget.pages_change.connect(self.on_pages_change)

        self._layout.addWidget(self.file_label, 0, Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self.list_widget)

        self._layout.addWidget(self.progress_bar)

        self.controls_widget = QWidget()
        self.controls_layout = QHBoxLayout(self.controls_widget)
        self.add_file_btn = QPushButton("Add File")
        self.add_file_btn.clicked.connect(self.open_file)

        self.pages_input = QLineEdit()
        self.pages_input.setPlaceholderText("pages (i.e 1,3-5,4)")
        self.pages_input.setEnabled(False)
        self.pages_input.textChanged.connect(self.calculate_indices)
        self.pages_input.textChanged.connect(self.re_render_thumbnails)

        self.split_btn = QPushButton("Split")
        self.split_btn.setEnabled(False)
        self.split_btn.clicked.connect(self.split)

        self.controls_layout.addWidget(self.add_file_btn)
        self.controls_layout.addStretch()
        self.controls_layout.addWidget(self.pages_input)
        self.controls_layout.addWidget(self.split_btn)

        self._layout.addWidget(self.controls_widget)

    def open_file(self) -> None:
        self.path, _ = QFileDialog.getOpenFileName(
            self, "Open File", QDir.homePath(), "PDFs (*.pdf)"
        )

        if len(self.path) < 1:
            return

        self.file_label.setText(f"File: {self.path}")
        self.list_widget.render_thumbnails()

    def on_pages_change(self, count: int) -> None:
        self.pages_input.setEnabled(count > 0)
        self.split_btn.setEnabled(count > 0)

    def calculate_indices(self, text: str) -> None:
        self.indices = calculate_indices(text)

    def re_render_thumbnails(self, text: str) -> None:
        if len(text) == 0 or self.indices is None:
            for i in range(self.list_widget.count()):
                self.list_widget.setRowHidden(i, False)

        else:
            for i in range(self.list_widget.count()):
                self.list_widget.setRowHidden(i, i not in self.indices)

    def split(self) -> None:
        if self.path is None:
            return
        if self.indices is None:
            QMessageBox.warning(self, "Error", "The input range cannot be empty")
            return
        self.worker = Worker(self.path, self.indices)
        self.worker.started.connect(self.progress_bar.show)
        self.worker.total_ready.connect(self.progress_bar.setMaximum)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.results_ready.connect(self.on_results)
        self.worker.done.connect(self.progress_bar.hide)
        self.worker.done.connect(self.progress_bar.reset)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_results(self, doc: PdfWriter) -> None:
        self.out_path, _ = QFileDialog.getSaveFileName(
            self, "Save as", QDir.homePath(), "PDFs (*.pdf)"
        )

        if not self.out_path.endswith(".pdf"):
            self.out_path = self.out_path + ".pdf"

        doc.write(self.out_path)

    def on_error(self, err: str) -> None:
        QMessageBox.warning(self, "Error", err)
