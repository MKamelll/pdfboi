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
)
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt, QDir, QThread, Signal, QSize
import fitz


class ViewerWorker(QThread):
    results_ready = Signal(fitz.Pixmap, int)
    progress = Signal(int)
    total_ready = Signal(int)

    def __init__(self, path: str):
        super().__init__()
        self.path = path

    def run(self):
        doc = fitz.open(self.path)
        self.total_ready.emit(doc.page_count)
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=fitz.Matrix(0.5, 0.5))
            self.results_ready.emit(pix, i)
            self.progress.emit(i + 1)


class ThumbnailWidget(QWidget):
    def __init__(self, pixmap: QPixmap, index: int):
        super().__init__()

        self._layout = QHBoxLayout(self)
        self.index = index
        self.label = QLabel(f"Page {self.index+1}")
        self.thum = QLabel()
        self.thum.setPixmap(pixmap)

        self._layout.addWidget(self.thum, 0, Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self.label, 0, Qt.AlignmentFlag.AlignCenter)


class SplitWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)

        self.file_label = QLabel("File:")
        self.pages_list = QListWidget()
        self.layout.addWidget(self.file_label, 0, Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.pages_list)

        self.progress_bar = QProgressBar()
        self.progress_bar.hide()

        self.layout.addWidget(self.progress_bar)

        self.controls_widget = QWidget()
        self.controls_layout = QHBoxLayout(self.controls_widget)
        self.add_file_btn = QPushButton("Add File")
        self.add_file_btn.clicked.connect(self.open_file)

        self.pages_input = QLineEdit()
        self.pages_input.setPlaceholderText("pages (i.e 1,3-5,4)")
        self.split_btn = QPushButton("Split")
        self.pages_input.setEnabled(False)
        self.split_btn.setEnabled(False)

        self.pages_list.model().rowsInserted.connect(self.on_pages_change)
        self.pages_list.model().rowsRemoved.connect(self.on_pages_change)

        self.controls_layout.addWidget(self.add_file_btn)
        self.controls_layout.addStretch()
        self.controls_layout.addWidget(self.pages_input)
        self.controls_layout.addWidget(self.split_btn)

        self.layout.addWidget(self.controls_widget)

    def open_file(self):
        self.path, _ = QFileDialog.getOpenFileName(
            self, "Open File", QDir.homePath(), "PDFs (*.pdf)"
        )
        self.file_label.setText(f"File: {self.path}")
        self.render_thumbnails()

    def render_thumbnails(self):
        self.viewer_worker = ViewerWorker(self.path)
        self.viewer_worker.total_ready.connect(self.progress_bar.setMaximum)
        self.viewer_worker.total_ready.connect(self.prepopulate_list)
        self.viewer_worker.progress.connect(self.progress_bar.setValue)
        self.viewer_worker.results_ready.connect(self.on_page_ready)
        self.viewer_worker.start()

    def prepopulate_list(self, count: int):
        for i in range(count):
            item = QListWidgetItem(self.pages_list)
            item.setSizeHint(QSize(120, 160))

    def on_page_ready(self, pix: fitz.Pixmap, index: int):
        img = QImage(
            pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888
        )
        pixmap = QPixmap.fromImage(img)

        item = self.pages_list.item(index)
        page = ThumbnailWidget(pixmap, index)
        item.setSizeHint(page.sizeHint())
        self.pages_list.setItemWidget(item, page)

    def on_pages_change(self):
        self.pages_input.setEnabled(self.pages_list.count() > 0)
        self.split_btn.setEnabled(self.pages_list.count() > 0)
