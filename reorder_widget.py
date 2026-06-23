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
from pdflist_widget import PdfListWidget
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
    def __init__(self) -> None:
        super().__init__()
        self._layout = QVBoxLayout(self)
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

        self._layout.addWidget(
            self.pages_reorder_widget, 0, Qt.AlignmentFlag.AlignCenter
        )

        self._layout.addWidget(self.progress_bar)

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

        self.controls_layout.addWidget(self.add_file_btn)
        self.controls_layout.addStretch()
        self.controls_layout.addWidget(self.reorder_btn)

        self._layout.addWidget(self.controls_widget)

    def open_file(self) -> None:
        self.path, _ = QFileDialog.getOpenFileName(
            self, "Open File", QDir.homePath(), "PDFs (*.pdf)"
        )
        if len(self.path) < 1:
            return
        self.file_label.setText(f"File: {self.path}")
        self.list_widget.render_thumbnails(self.path)

    def on_pages_change(self):
        pages_not_empty = self.list_widget.count() > 0
        self.up_btn.setEnabled(pages_not_empty)
        self.down_btn.setEnabled(pages_not_empty)
        self.reorder_btn.setEnabled(pages_not_empty)

    def move_page_up(self) -> None:
        row = self.list_widget.currentRow()
        if row <= 0:
            return

        widget = self.list_widget.itemWidget(self.list_widget.item(row))
        if not isinstance(widget, ThumbnailWidget):
            return
        index, bitmap = widget.index, widget.bitmap
        item = self.list_widget.takeItem(row)
        self.list_widget.insertItem(row - 1, item)
        new_widget = ThumbnailWidget(bitmap, index, self.list_widget)
        self.list_widget.setItemWidget(item, new_widget)
        self.list_widget.setCurrentRow(row - 1)

    def move_page_down(self):
        row = self.list_widget.currentRow()
        if row >= self.list_widget.count() - 1:
            return

        widget = self.list_widget.itemWidget(self.list_widget.item(row))
        if not isinstance(widget, ThumbnailWidget):
            return
        index, bitmap = widget.index, widget.bitmap
        item = self.list_widget.takeItem(row)
        self.list_widget.insertItem(row + 1, item)
        new_widget = ThumbnailWidget(bitmap, index, self.list_widget)
        self.list_widget.setItemWidget(item, new_widget)
        self.list_widget.setCurrentRow(row + 1)

    def reorder(self):
        indices: list[int] = []
        for i in range(self.list_widget.count()):
            widget = self.list_widget.itemWidget(self.list_widget.item(i))
            if not isinstance(widget, ThumbnailWidget):
                continue
            indices.append(widget.index)

        self.worker = Worker(self.path, indices)
        self.worker.total_ready.connect(self.progress_bar.setMaximum)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.results_ready.connect(self.on_results)
        self.worker.results_ready.connect(self.progress_bar.hide)
        self.worker.results_ready.connect(self.progress_bar.reset)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_results(self, doc: PdfWriter):
        self.out_path, _ = QFileDialog.getSaveFileName(
            self, "Save as", QDir.homePath(), "PDFs (*.pdf)"
        )
        if len(self.out_path) < 1:
            return
        if not self.out_path.endswith(".pdf"):
            self.out_path = self.out_path + ".pdf"
        doc.write(self.out_path)

    def on_error(self, err: str) -> None:
        QMessageBox.warning(self, "Error", err)
