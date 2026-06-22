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
from thumbnailwidget import ThumbnailWidget, ThumbnailWorker


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
        self.pages_input.setEnabled(False)
        self.pages_input.textChanged.connect(self.calculate_indices)
        self.pages_input.textChanged.connect(self.re_render_thumbnails)

        self.split_btn = QPushButton("Split")
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
        self.viewer_worker = ThumbnailWorker(self.path)
        self.viewer_worker.total_ready.connect(self.progress_bar.setMaximum)
        self.viewer_worker.total_ready.connect(self.set_initial_indices)
        self.viewer_worker.total_ready.connect(self.prepopulate_list)
        self.viewer_worker.progress.connect(self.progress_bar.setValue)
        self.viewer_worker.results_ready.connect(self.on_page_ready)
        self.viewer_worker.start()

    def set_initial_indices(self, count: int):
        self.page_count = count
        self.pages_indices = [i for i in range(count)]

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

    def calculate_indices(self, text: str):
        gps = text.split(",")
        results = set()
        try:
            for g in gps:
                if "-" in g:
                    parts = g.split("-")
                    if len(parts) == 2:
                        start, end = int(parts[0]) - 1, int(parts[1]) - 1
                        start = max(0, min(start, self.page_count))
                        end = max(0, min(end, self.page_count))
                        for i in range(start, end + 1):
                            results.add(i)
                else:
                    g_int = max(0, min(int(g) - 1, self.page_count))
                    results.add(g_int)
        except ValueError:
            pass

        self.pages_indices = list(results)

    def re_render_thumbnails(self, text: str):
        if len(text) == 0:
            for i in range(self.pages_list.count()):
                self.pages_list.setRowHidden(i, False)

        else:
            for i in range(self.pages_list.count()):
                self.pages_list.setRowHidden(i, i not in self.pages_indices)
