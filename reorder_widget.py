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

    def __init__(self, path: str, indices: list[int]):
        super().__init__()
        self.path = path
        self.indices = indices

    def run(self):
        src_doc = PdfReader(self.path)
        out_doc = PdfWriter()

        self.total_ready.emit(len(self.indices))

        for i, index in enumerate(self.indices):
            out_doc.append(src_doc, [index])
            self.progress.emit(i + 1)

        self.results_ready.emit(out_doc)


class ReorderWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)

        self.file_label = QLabel("File:")
        self.pages_list = QListWidget()
        self.layout.addWidget(self.file_label, 0, Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.pages_list)

        self.pages_reorder_widget = QWidget()
        self.pages_reorder_layout = QHBoxLayout(self.pages_reorder_widget)

        self.up_btn = QPushButton("Up")
        self.up_btn.setToolTip("Alt+Up")
        self.up_btn.setEnabled(False)
        self.up_btn.clicked.connect(self.move_page_up)
        self.pages_reorder_layout.addWidget(self.up_btn)

        self.down_btn = QPushButton("Down")
        self.down_btn.setToolTip("Alt+Down")
        self.down_btn.setEnabled(False)
        self.down_btn.clicked.connect(self.move_page_down)
        self.pages_reorder_layout.addWidget(self.down_btn)

        self.layout.addWidget(
            self.pages_reorder_widget, 0, Qt.AlignmentFlag.AlignCenter
        )

        self.progress_bar = QProgressBar()
        self.progress_bar.hide()

        self.layout.addWidget(self.progress_bar)

        self.controls_widget = QWidget()
        self.controls_layout = QHBoxLayout(self.controls_widget)
        self.add_file_btn = QPushButton("Add File")
        self.add_file_btn.clicked.connect(self.open_file)

        QShortcut(QKeySequence("Alt+Up"), self).activated.connect(
            self.up_btn.animateClick
        )
        QShortcut(QKeySequence("Alt+Down"), self).activated.connect(
            self.down_btn.animateClick
        )

        self.reorder_btn = QPushButton("Reorder")
        self.reorder_btn.setEnabled(False)
        self.reorder_btn.clicked.connect(self.reorder)

        self.pages_list.model().rowsInserted.connect(self.on_pages_change)
        self.pages_list.model().rowsRemoved.connect(self.on_pages_change)

        self.controls_layout.addWidget(self.add_file_btn)
        self.controls_layout.addStretch()
        self.controls_layout.addWidget(self.reorder_btn)

        self.layout.addWidget(self.controls_widget)

    def open_file(self):
        self.path, _ = QFileDialog.getOpenFileName(
            self, "Open File", QDir.homePath(), "PDFs (*.pdf)"
        )
        self.file_label.setText(f"File: {self.path}")
        self.render_thumbnails()

    def render_thumbnails(self):
        self.progress_bar.show()
        self.viewer_worker = ThumbnailWorker(self.path)
        self.viewer_worker.total_ready.connect(self.progress_bar.setMaximum)
        self.viewer_worker.total_ready.connect(self.set_initial_indices)
        self.viewer_worker.total_ready.connect(self.prepopulate_list)
        self.viewer_worker.progress.connect(self.progress_bar.setValue)
        self.viewer_worker.results_ready.connect(self.on_page_ready)
        self.viewer_worker.start()

    def set_initial_indices(self, count: int):
        self.page_count = count
        self.pages_indices: list[int] = []

    def prepopulate_list(self, count: int):
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
        self.up_btn.setEnabled(pages_not_empty)
        self.down_btn.setEnabled(pages_not_empty)
        self.reorder_btn.setEnabled(pages_not_empty)

    def move_page_up(self):
        row = self.pages_list.currentRow()
        if row <= 0:
            return

        widget = self.pages_list.itemWidget(self.pages_list.item(row))
        index, bitmap = widget.index, widget.bitmap
        item = self.pages_list.takeItem(row)
        self.pages_list.insertItem(row - 1, item)
        new_widget = ThumbnailWidget(bitmap, index, self.pages_list)
        self.pages_list.setItemWidget(item, new_widget)
        self.pages_list.setCurrentRow(row - 1)

    def move_page_down(self):
        row = self.pages_list.currentRow()
        if row >= self.pages_list.count() - 1:
            return

        widget = self.pages_list.itemWidget(self.pages_list.item(row))
        index, bitmap = widget.index, widget.bitmap
        item = self.pages_list.takeItem(row)
        self.pages_list.insertItem(row + 1, item)
        new_widget = ThumbnailWidget(bitmap, index, self.pages_list)
        self.pages_list.setItemWidget(item, new_widget)
        self.pages_list.setCurrentRow(row + 1)

    def reorder(self):
        indices: list[int] = []
        for i in range(self.pages_list.count()):
            widget = self.pages_list.itemWidget(self.pages_list.item(i))
            indices.append(widget.index)

        self.worker = Worker(self.path, indices)
        self.worker.total_ready.connect(self.progress_bar.setMaximum)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.results_ready.connect(self.on_results)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_results(self, doc: PdfWriter):
        self.progress_bar.hide()
        self.progress_bar.reset()
        self.out_path, _ = QFileDialog.getSaveFileName(
            self, "Save as", QDir.homePath(), "PDFs (*.pdf)"
        )
        if not self.out_path.endswith(".pdf"):
            self.out_path = self.out_path + ".pdf"
        doc.write(self.out_path)

    def on_error(self, err: str):
        QMessageBox.warning(self, "Error", err)
