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
from PySide6.QtGui import QImage, QPixmap, QTransform
from PySide6.QtCore import Qt, QDir, QThread, Signal, QSize
import pypdfium2 as pypdfium


class ThumbnailWorker(QThread):
    results_ready = Signal(pypdfium.PdfBitmap, int)
    progress = Signal(int)
    total_ready = Signal(int)
    done = Signal()

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

        self.done.emit()


class ThumbnailWidget(QWidget):
    def __init__(
        self, bitmap: pypdfium.PdfBitmap, index: int, parent: QWidget | None = None
    ):
        super().__init__(parent=parent)

        self.index = index
        self.bitmap = bitmap
        self.rotation = 0

        self._layout = QHBoxLayout(self)
        self.label = QLabel(f"Page {self.index + 1}")

        data = self.bitmap.to_pil().convert("RGB").tobytes()
        img = QImage(
            data,
            self.bitmap.width,
            self.bitmap.height,
            self.bitmap.width * 3,
            QImage.Format.Format_RGB888,
        )
        self.pixmap = QPixmap.fromImage(img)

        self.thum = QLabel()
        self.thum.setPixmap(self.pixmap)

        self._layout.addWidget(self.thum, 0, Qt.AlignmentFlag.AlignCenter)
        self._layout.addWidget(self.label, 0, Qt.AlignmentFlag.AlignCenter)

    def rotate(self, angle: int):
        self.rotation = (self.rotation + angle) % 360
        rotated = self.pixmap.transformed(QTransform().rotate(self.rotation))
        self.thum.setPixmap(rotated)
