from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
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


class Worker(QThread):
    results_ready = Signal(PdfWriter)
    progress = Signal(int)
    total_ready = Signal(int)
    error = Signal(str)

    def __init__(self, files: list[str]):
        super().__init__()
        self.files = files

    def run(self) -> None:
        if len(self.files) < 1:
            self.error.emit("Files cannot be empty")

        self.total_ready.emit(len(self.files))

        merger = PdfWriter()

        for i, path in enumerate(self.files):
            merger.append(path)
            self.progress.emit(i + 1)

        self.results_ready.emit(merger)


class ConvertToWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._layout = QVBoxLayout(self)
        self.file_list = QListWidget()
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()

        self.controls_widget = QWidget()
        self.controls_layout = QHBoxLayout(self.controls_widget)

        self.add_files_btn = QPushButton("Add Files")
        self.add_files_btn.clicked.connect(self.open_files)
        self.controls_layout.addWidget(self.add_files_btn)
        self.controls_layout.addStretch()
        self.convert_btn = QPushButton("Convert")
        self.convert_btn.setEnabled(False)
        self.convert_btn.clicked.connect(self.convert_files)
        self.controls_layout.addWidget(self.convert_btn)

        self.file_list.model().rowsInserted.connect(
            lambda _: self.convert_btn.setEnabled(self.file_list.count() > 0)
        )

        self.file_list.model().rowsRemoved.connect(
            lambda _: self.convert_btn.setEnabled(self.file_list.count() > 0)
        )

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

        self._layout.addWidget(self.file_list)
        self._layout.addStretch()
        self._layout.addWidget(self.out_types_widget)
        self._layout.addWidget(self.progress_bar)
        self._layout.addWidget(self.controls_widget)

    def open_files(self) -> None:
        self.paths, _ = QFileDialog.getOpenFileNames(
            self, "Open Files", QDir.homePath(), "PDFs (*.pdf)"
        )

        if len(self.paths) == 0:
            return

        self.file_list.addItems(self.paths)

    def convert_files(self) -> None:
        self.worker = Worker(
            [self.file_list.item(i).text() for i in range(self.file_list.count())]
        )
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
