from PySide6.QtCore import QThread, Signal
import arabic_reshaper
import openpyxl
import pdfplumber
import regex


class ExcelWorker(QThread):
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
        return bool(regex.search(r"\p{Arabic}", text))

    def normalize_numbers(self, text: str) -> str:
        table = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
        return text.translate(table)

    def fix_rtl(self, text: str) -> str:
        if len(text) < 1:
            return text

        text = self.normalize_numbers(text)
        text = " ".join(text.split())
        tokens = regex.split(r"(\P{Arabic}+)", text)
        fixed = []
        for token in tokens:
            token = token.strip()
            if self.needs_arabic_fix(token):
                reshaped = arabic_reshaper.reshape(token)
                fixed.append(reshaped)
            else:
                fixed.append(token[::-1])

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
                r = [self.fix_rtl(cell) for cell in r]
            if self.rtl:
                r.reverse()
            ws.append(r)

        self.results_ready.emit(wb)
