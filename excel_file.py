from os import preadv

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

    def extract_rows_rtl(self) -> list[list[str | None]]:
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
                tables = page.extract_tables()
                table_objects = page.find_tables()
                for table_obj, table_data in zip(table_objects, tables):
                    for i, row in enumerate(table_obj.rows):
                        for j, cell in enumerate(row.cells):
                            if cell is None:
                                continue
                            cell_chars = page.crop(cell).chars
                            word = []
                            words = []
                            lines = []
                            avg_char_width = (
                                sum(c["width"] for c in cell_chars if c["text"] != " ")
                                / len(cell_chars)
                                if cell_chars
                                else 5
                            )
                            w_threshold = avg_char_width * 0.5
                            avg_char_height = (
                                sum(c["height"] for c in cell_chars) / len(cell_chars)
                                if cell_chars
                                else 5
                            )
                            prev_char = None
                            for char in cell_chars:
                                if (
                                    prev_char is not None
                                    and abs(char["y0"] - prev_char["y0"])
                                    > avg_char_height
                                ):
                                    if word:
                                        words.append("".join(word[::-1]))
                                        word = []
                                    if words:
                                        lines.append(" ".join(words[::-1]))
                                        words = []

                                if char["text"] == " " and char["width"] < w_threshold:
                                    continue
                                elif char["text"] == " ":
                                    if word:
                                        words.append("".join(word[::-1]))
                                        word = []
                                else:
                                    word.append(char["text"])

                                prev_char = char

                            if word:
                                words.append("".join(word[::-1]))

                            if words:
                                lines.append(" ".join(words[::-1]))

                            table_data[i][j] = " ".join(lines)

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

    def extract_rows(self) -> list[list[str | None]]:
        if self.rtl:
            return self.extract_rows_rtl()

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
        tokens = regex.split(r"(\P{Arabic}+)", text)
        fixed = []
        others = []
        for token in tokens:
            token = token.strip()
            if self.needs_arabic_fix(token):
                reshaped = arabic_reshaper.reshape(token)
                fixed.append(reshaped)
            else:
                others.append(token[::-1])

        return " ".join(
            [t for t in fixed if t.strip()] + [t for t in others if t.strip()]
        )

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
