from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QLabel,
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
    QProgressBar,
    QMessageBox,
)
from PySide6.QtCore import Qt, QDir, QThread, Signal
from pypdf import PdfWriter

from pdflist_widget import PdfListWidget


class Worker(QThread):
    results_ready = Signal(PdfWriter)
    progress = Signal(int)
    total_ready = Signal(int)
    error = Signal(str)

    def __init__(self, path: str):
        super().__init__()
        self.path = path

    def run(self) -> None:
        pass


class ConvertToWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._layout = QVBoxLayout(self)
        self.path: str | None = None
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

        self.controls_widget = QWidget()
        self.controls_layout = QHBoxLayout(self.controls_widget)

        self.add_file_btn = QPushButton("Add File")
        self.add_file_btn.clicked.connect(self.open_file)
        self.controls_layout.addWidget(self.add_file_btn)
        self.controls_layout.addStretch()
        self.convert_btn = QPushButton("Convert")
        self.convert_btn.setEnabled(False)
        self.convert_btn.clicked.connect(self.convert_file)
        self.controls_layout.addWidget(self.convert_btn)

        self.out_types_widget = QWidget()
        self.out_types_layout = QHBoxLayout(self.out_types_widget)
        self.out_types = ["Excel (.xlsx)", "Word (.docx)"]
        self.combo_box = QComboBox()
        self.combo_box.addItems(self.out_types)
        self.headers_check_box = QCheckBox("Headers")
        self.headers_check_box.setToolTip(
            "Uncheck this if the tables don't have headers"
        )
        self.headers_check_box.setChecked(True)
        self.headers_check_box.setVisible(self.combo_box.currentIndex() == 0)
        self.combo_box.currentIndexChanged.connect(
            lambda i: self.headers_check_box.setVisible(i == 0)
        )
        self.out_types_layout.addWidget(self.combo_box)
        self.out_types_layout.addStretch()
        self.out_types_layout.addWidget(self.headers_check_box)

        self._layout.addWidget(self.out_types_widget)
        self._layout.addWidget(self.progress_bar)
        self._layout.addWidget(self.controls_widget)

    def on_pages_change(self, count: int) -> None:
        self.convert_btn.setEnabled(count > 0)

    def open_file(self) -> None:
        self.path, _ = QFileDialog.getOpenFileName(
            self, "Open Files", QDir.homePath(), "PDFs (*.pdf)"
        )

        if len(self.path) < 1:
            return

        self.list_widget.render_thumbnails(self.path)

    def convert_file(self) -> None:
        self.worker = Worker(self.path)
        self.worker.started.connect(self.progress_bar.show)
        self.worker.total_ready.connect(self.progress_bar.setMaximum)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.results_ready.connect(self.on_results)
        self.worker.results_ready.connect(self.progress_bar.hide)
        self.worker.results_ready.connect(self.progress_bar.reset)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_results(self, doc: PdfWriter) -> None:
        self.out_path, _ = QFileDialog.getSaveFileName(
            self, "Save as", QDir.homePath(), "PDFs (*.pdf)"
        )
        doc.write(self.out_path + ".pdf")

    def on_error(self, err: str) -> None:
        QMessageBox.warning(self, "Error", err)
