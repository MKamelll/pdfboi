from PySide6.QtCore import QSize, Signal
from PySide6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from thumbnailwidget import ThumbnailWidget, ThumbnailWorker
import pypdfium2 as pypdfium


class PdfViewerWidget(QWidget):
    pages_change = Signal(int)
    started = Signal()
    progress_max = Signal(int)
    progress_update = Signal(int)
    done = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__()
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        self.pages_list = QListWidget(self)
        self.path: str | None = None

        self.pages_list.model().rowsInserted.connect(
            lambda _: self.pages_change.emit(self.pages_list.count())
        )
        self.pages_list.model().rowsRemoved.connect(
            lambda _: self.pages_change.emit(self.pages_list.count())
        )

        self._layout.addWidget(self.pages_list)

    def render_thumbnails(self, path: str) -> None:
        self.path = path
        self.viewer_worker = ThumbnailWorker(self.path)
        self.viewer_worker.started.connect(self.started)
        self.viewer_worker.total_ready.connect(self.progress_max)
        self.viewer_worker.total_ready.connect(self.set_initial_indices)
        self.viewer_worker.total_ready.connect(self.prepopulate_list)
        self.viewer_worker.progress.connect(self.progress_update)
        self.viewer_worker.results_ready.connect(self.on_page_ready)
        self.viewer_worker.done.connect(self.done)
        self.viewer_worker.start()

    def set_initial_indices(self, count: int) -> None:
        self.page_count = count
        self.pages_indices: list[int] = []

    def prepopulate_list(self, count: int) -> None:
        for i in range(count):
            item = QListWidgetItem(self.pages_list)
            item.setSizeHint(QSize(120, 160))

    def on_page_ready(self, pix: pypdfium.PdfBitmap, index: int) -> None:
        item = self.pages_list.item(index)
        page = ThumbnailWidget(pix, index)
        item.setSizeHint(page.sizeHint())
        self.pages_list.setItemWidget(item, page)

    def listCount(self) -> int:
        return self.pages_list.count()

    def setRowHidden(self, index: int, state: bool):
        self.pages_list.setRowHidden(index, state)
