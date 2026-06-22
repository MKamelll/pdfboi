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
import pypdfium2 as pypdfium


class ThumbnailWorker(QThread):
    results_ready = Signal(pypdfium.PdfBitmap, int)
    progress = Signal(int)
    total_ready = Signal(int)

    def __init__(self, path: str):
        super().__init__()
        self.path = path

    def run(self):
        doc = pypdfium.PdfDocument(self.path)
        self.total_ready.emit(len(doc))

        for i, page in enumerate(doc):
            pix = page.render(scale=0.5)
            self.results_ready.emit(pix, i)
            self.progress.emit(i + 1)


class ThumbnailWidget(QWidget):
    def __init__(self, pixmap: pypdfium.PdfBitmap, index: int):
        super().__init__()

        self._layout = QHBoxLayout(self)
        self.index = index
        self.label = QLabel(f"Page {self.index+1}")

        data = pixmap.to_pil().convert("RGB").tobytes()
        img = QImage(
            data,
            pixmap.width,
            pixmap.height,
            pixmap.width * 3,
            QImage.Format.Format_RGB888,
        )
        pixmap = QPixmap.fromImage(img)

        self.thum = QLabel()
        self.thum.setPixmap(pixmap)

        self._layout.addWidget(self.thum, 0, Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self.label, 0, Qt.AlignmentFlag.AlignCenter)
