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
from PySide6.QtGui import QImage, QPixmap, QShortcut, QKeySequence
from PySide6.QtCore import Qt, QDir, QThread, Signal, QSize
from thumbnailwidget import ThumbnailWidget, ThumbnailWorker
from pypdf import PdfWriter, PdfReader
import pypdfium2 as pypdfium


class Worker(QThread):
    results_ready = Signal(PdfWriter)
    progress = Signal(int)
    total_ready = Signal(int)
    error = Signal(str)

    def __init__(self, path: str, transform: list[tuple[int, int]]):
        super().__init__()
        self.path = path
        self.transform = transform

    def run(self):
        src_doc = PdfReader(self.path)
        out_doc = PdfWriter()

        self.total_ready.emit(len(self.transform))

        for i, (index, rotation) in enumerate(self.transform):
            out_doc.add_page(src_doc.pages[index])
            out_doc.pages[index].rotate(rotation)
            self.progress.emit(i + 1)

        self.results_ready.emit(out_doc)


class RotateWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._layout = QVBoxLayout(self)

        self.file_label = QLabel("File:")
        self.pages_list = QListWidget()
        self._layout.addWidget(self.file_label, 0, Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self.pages_list)

        self.page_rotate_widget = QWidget()
        self.page_rotate_layout = QHBoxLayout(self.page_rotate_widget)

        self.rotate_right_btn = QPushButton("Right")
        self.rotate_right_btn.setToolTip("Alt+Right")
        self.rotate_right_btn.setEnabled(False)
        self.rotate_right_btn.clicked.connect(self.rotate_page_right)

        self.rotate_left_btn = QPushButton("Left")
        self.rotate_left_btn.setToolTip("Alt+Left")
        self.rotate_left_btn.setEnabled(False)
        self.rotate_left_btn.clicked.connect(self.rotate_page_left)

        self.page_rotate_layout.addWidget(self.rotate_left_btn)
        self.page_rotate_layout.addWidget(self.rotate_right_btn)

        self._layout.addWidget(self.page_rotate_widget, 0, Qt.AlignmentFlag.AlignCenter)

        self.progress_bar = QProgressBar()
        self.progress_bar.hide()

        self._layout.addWidget(self.progress_bar)

        self.controls_widget = QWidget()
        self.controls_layout = QHBoxLayout(self.controls_widget)
        self.add_file_btn = QPushButton("Add File")
        self.add_file_btn.clicked.connect(self.open_file)

        QShortcut(QKeySequence("Alt+Right"), self).activated.connect(
            self.rotate_right_btn.animateClick
        )
        QShortcut(QKeySequence("Alt+Left"), self).activated.connect(
            self.rotate_left_btn.animateClick
        )

        self.rotate_btn = QPushButton("Rotate")
        self.rotate_btn.setEnabled(False)
        self.rotate_btn.clicked.connect(self.rotate)

        self.pages_list.model().rowsInserted.connect(self.on_pages_change)
        self.pages_list.model().rowsRemoved.connect(self.on_pages_change)

        self.controls_layout.addWidget(self.add_file_btn)
        self.controls_layout.addStretch()
        self.controls_layout.addWidget(self.rotate_btn)

        self._layout.addWidget(self.controls_widget)

    def open_file(self) -> None:
        self.path, _ = QFileDialog.getOpenFileName(
            self, "Open File", QDir.homePath(), "PDFs (*.pdf)"
        )
        self.file_label.setText(f"File: {self.path}")
        self.render_thumbnails()

    def render_thumbnails(self) -> None:
        self.progress_bar.show()
        self.viewer_worker = ThumbnailWorker(self.path)
        self.viewer_worker.total_ready.connect(self.progress_bar.setMaximum)
        self.viewer_worker.total_ready.connect(self.set_initial_indices)
        self.viewer_worker.total_ready.connect(self.prepopulate_list)
        self.viewer_worker.progress.connect(self.progress_bar.setValue)
        self.viewer_worker.results_ready.connect(self.on_page_ready)
        self.viewer_worker.start()

    def set_initial_indices(self, count: int) -> None:
        self.page_count = count
        self.pages_indices: list[int] = []

    def prepopulate_list(self, count: int) -> None:
        for i in range(count):
            item = QListWidgetItem(self.pages_list)
            item.setSizeHint(QSize(120, 160))

    def on_page_ready(self, pix: pypdfium.PdfBitmap, index: int):
        if index == self.page_count - 1:
            self.progress_bar.hide()

        item = self.pages_list.item(index)
        page = ThumbnailWidget(pix, index, self.pages_list)
        item.setSizeHint(page.sizeHint())
        self.pages_list.setItemWidget(item, page)

    def on_pages_change(self):
        pages_not_empty = self.pages_list.count() > 0
        self.rotate_right_btn.setEnabled(pages_not_empty)
        self.rotate_left_btn.setEnabled(pages_not_empty)
        self.rotate_btn.setEnabled(pages_not_empty)

    def rotate_page_right(self) -> None:
        row = self.pages_list.currentRow()
        widget = self.pages_list.itemWidget(self.pages_list.item(row))
        if not isinstance(widget, ThumbnailWidget):
            return
        widget.rotate(90)
        self.pages_list.item(row).setSizeHint(widget.sizeHint())

    def rotate_page_left(self):
        row = self.pages_list.currentRow()

        widget = self.pages_list.itemWidget(self.pages_list.item(row))
        if not isinstance(widget, ThumbnailWidget):
            return

        widget.rotate(-90)
        self.pages_list.item(row).setSizeHint(widget.sizeHint())

    def rotate(self):
        transform: list[tuple[int, int]] = []
        for i in range(self.pages_list.count()):
            widget = self.pages_list.itemWidget(self.pages_list.item(i))
            if not isinstance(widget, ThumbnailWidget):
                continue
            transform.append((widget.index, widget.rotation))

        self.worker = Worker(self.path, transform)
        self.worker.started.connect(self.progress_bar.show)
        self.worker.total_ready.connect(self.progress_bar.setMaximum)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.results_ready.connect(self.progress_bar.hide)
        self.worker.results_ready.connect(self.progress_bar.reset)
        self.worker.results_ready.connect(self.on_results)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_results(self, doc: PdfWriter):
        self.out_path, _ = QFileDialog.getSaveFileName(
            self, "Save as", QDir.homePath(), "PDFs (*.pdf)"
        )
        if not self.out_path.endswith(".pdf"):
            self.out_path = self.out_path + ".pdf"
        doc.write(self.out_path)

    def on_error(self, err: str) -> None:
        QMessageBox.warning(self, "Error", err)
