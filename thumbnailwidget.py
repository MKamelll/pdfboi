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


class ThumbnailWorker(QThread):
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
