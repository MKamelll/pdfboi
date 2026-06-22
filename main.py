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
)
from PySide6.QtCore import Qt, QDir
import sys
from merge_widget import MergeWidget
from split_widget import SplitWidget
from delete_widget import DeleteWidget
from reorder_widget import ReorderWidget


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self._layout = QVBoxLayout(self)

        self.left_widget = QWidget()
        self.left_box = QVBoxLayout(self.left_widget)
        self.right_widget = QWidget()
        self.right_box = QVBoxLayout(self.right_widget)
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.left_widget)
        self.splitter.addWidget(self.right_widget)
        self.splitter.setSizes([150, 450])
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.stack = QStackedWidget()

        self.actions = ["Merge", "Split", "Reorder", "Delete"]
        self.left_box_list = QListWidget()
        self.left_box_list.addItems(self.actions)
        self.left_box_list.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.left_box.addWidget(self.left_box_list)

        self.right_box.addWidget(self.stack)

        self.merge_widget = MergeWidget()
        self.split_widget = SplitWidget()
        self.reorder_widget = ReorderWidget()
        self.delete_widget = DeleteWidget()

        self.stack.addWidget(self.merge_widget)
        self.stack.addWidget(self.split_widget)
        self.stack.addWidget(self.reorder_widget)
        self.stack.addWidget(self.delete_widget)

        self._layout.addWidget(self.splitter)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(640, 460)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
