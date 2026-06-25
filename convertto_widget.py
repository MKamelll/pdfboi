from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QLabel,
    QLineEdit,
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
from util import calculate_indices
import pdfplumber
import openpyxl
import arabic_reshaper
from bidi.algorithm import StrOrBytes, get_display
import re


class Worker(QThread):
    results_ready = Signal(openpyxl.Workbook)
    progress = Signal(int)
    total_ready = Signal(int)
    error = Signal(str)

    def __init__(
        self,
        path: str,
        indices: list[int] | None = None,
        has_headers: bool = True,
        rtl: bool = False,
    ):
        super().__init__()
        self.path = path
        self.indices = indices
        self.has_headers = has_headers
        self.rtl = rtl

    def extract_rows(self) -> list[list[str | None]]:
        all_rows: list[list[str | None]] = []
        headers = None

        with pdfplumber.open(self.path) as pdf:
            pages = (
                [pdf.pages[i] for i in self.indices]
                if self.indices is not None
                else pdf.pages
            )

            self.total_ready.emit(len(pages))

            for i, page in enumerate(pages):
                if self.rtl:
                    tables = page.extract_tables(dict(text_char_dir_render="rtl"))
                else:
                    tables = page.extract_tables()
                for table in tables:
                    if not table:
                        continue

                    if self.has_headers:
                        if headers is None:
                            headers = table[0]
                            all_rows.append(headers)
                            all_rows.extend(table[1:])
                        elif headers == table[0]:
                            all_rows.extend(table[1:])
                        else:
                            all_rows.extend(table)

                    else:
                        all_rows.extend(table)

                self.progress.emit(i + 1)

        return all_rows

    def needs_arabic_fix(self, text: str) -> bool:
        if len(text) < 1:
            return False
        return any("\u0600" <= c <= "\u06ff" for c in text)

    def normalize_numbers(self, text: str) -> str:
        table = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
        return text.translate(table)

    def fix_cell(self, text: str) -> str:
        if len(text) < 1:
            return text

        text = self.normalize_numbers(text)
        tokens = re.split(r"(\d+\.?\d*)", text)
        fixed = []
        for token in tokens:
            token = token.strip()
            if re.match(r"\d+\.?\d*", token):
                fixed.append(token[::-1])
            elif self.needs_arabic_fix(token):
                fixed.append(arabic_reshaper.reshape(token))
            else:
                fixed.append(token)

        return " ".join([t for t in fixed if t.strip()])

    def run(self) -> None:
        all_rows = self.extract_rows()
        wb = openpyxl.Workbook()
        ws = wb.active

        if ws is None:
            self.error.emit("Workbook doesn't have any sheets")
            return

        ws.sheet_view.rightToLeft = self.rtl
        for row in all_rows:
            r = [cell if cell is not None else "" for cell in row]
            if self.rtl:
                r = [self.fix_cell(cell) for cell in r]
            if self.rtl:
                r.reverse()
            ws.append(r)

        self.results_ready.emit(wb)


class ConvertToWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._layout = QVBoxLayout(self)
        self.path: str | None = None
        self.indices: list[int] | None = None
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

        self.pages_input = QLineEdit()
        self.pages_input.setPlaceholderText("table pages (i.e 1,3-5,4)")
        self.pages_input.setToolTip(
            "If left empty, the whole file is treated as one table"
        )
        self.pages_input.setEnabled(False)
        self.pages_input.textChanged.connect(self.calculate_indices)
        self.pages_input.textChanged.connect(self.re_render_thumbnails)

        self.add_file_btn = QPushButton("Add File")
        self.add_file_btn.clicked.connect(self.open_file)
        self.convert_btn = QPushButton("Convert")
        self.convert_btn.setEnabled(False)
        self.convert_btn.clicked.connect(self.convert_file)

        self.controls_layout.addWidget(self.add_file_btn)
        self.controls_layout.addStretch()
        self.controls_layout.addWidget(self.pages_input)
        self.controls_layout.addWidget(self.convert_btn)

        self.out_types_widget = QWidget()
        self.out_types_layout = QHBoxLayout(self.out_types_widget)
        self.out_types = ["Excel (.xlsx)", "Word (.docx)"]
        self.combo_box = QComboBox()
        self.combo_box.addItems(self.out_types)

        self.rtl_check_box = QCheckBox("RtL")
        self.rtl_check_box.setToolTip("Check if the sheet is in Right-To-Left language")
        self.rtl_check_box.setChecked(False)
        self.rtl_check_box.setVisible(self.combo_box.currentIndex() == 0)

        self.headers_check_box = QCheckBox("Headers")
        self.headers_check_box.setToolTip(
            "Uncheck this if the tables don't have headers"
        )
        self.headers_check_box.setChecked(True)
        self.headers_check_box.setVisible(self.combo_box.currentIndex() == 0)
        self.combo_box.currentIndexChanged.connect(self.on_type_changed)

        self.out_types_layout.addWidget(self.combo_box)
        self.out_types_layout.addStretch()
        self.out_types_layout.addWidget(self.rtl_check_box)
        self.out_types_layout.addWidget(self.headers_check_box)

        self._layout.addWidget(self.out_types_widget)
        self._layout.addWidget(self.progress_bar)
        self._layout.addWidget(self.controls_widget)

    def on_type_changed(self, index: int) -> None:
        self.headers_check_box.setVisible(index == 0)
        self.rtl_check_box.setVisible(index == 0)

    def calculate_indices(self, text: str) -> None:
        self.indices = calculate_indices(text, self.list_widget.count())

    def re_render_thumbnails(self, text: str) -> None:
        if len(text) == 0 or self.indices is None:
            for i in range(self.list_widget.count()):
                self.list_widget.setRowHidden(i, False)

        else:
            for i in range(self.list_widget.count()):
                self.list_widget.setRowHidden(i, i not in self.indices)

    def on_pages_change(self, count: int) -> None:
        self.convert_btn.setEnabled(count > 0)
        self.pages_input.setEnabled(count > 0)

    def open_file(self) -> None:
        self.path, _ = QFileDialog.getOpenFileName(
            self, "Open File", QDir.homePath(), "PDFs (*.pdf)"
        )

        if len(self.path) < 1:
            return

        self.file_label.setText(f"File: {self.path}")
        self.list_widget.render_thumbnails(self.path)

    def convert_file(self) -> None:
        if self.path is None:
            return
        has_headers = self.headers_check_box.isChecked()
        rtl = self.rtl_check_box.isChecked()
        self.worker = Worker(
            self.path, indices=self.indices, has_headers=has_headers, rtl=rtl
        )
        self.worker.started.connect(self.progress_bar.show)
        self.worker.total_ready.connect(self.progress_bar.setMaximum)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.results_ready.connect(self.on_results)
        self.worker.results_ready.connect(self.progress_bar.hide)
        self.worker.results_ready.connect(self.progress_bar.reset)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_results(self, wb: openpyxl.Workbook) -> None:
        self.out_path, _ = QFileDialog.getSaveFileName(
            self, "Save as", QDir.homePath(), "Excel (*.xlsx)"
        )
        if len(self.out_path) < 1:
            return

        if not self.out_path.endswith(".xlsx"):
            self.out_path += ".xlsx"

        wb.save(self.out_path)

    def on_error(self, err: str) -> None:
        QMessageBox.warning(self, "Error", err)
