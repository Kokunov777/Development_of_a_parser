from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QTextCharFormat, QSyntaxHighlighter
from PySide6.QtWidgets import (
    QPlainTextEdit,
    QSplitter,
    QTabWidget,
    QTableWidget,
    QTextEdit,
    QWidget,
)


class SimpleSyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.keywords = [
            "if",
            "else",
            "while",
            "for",
            "return",
            "def",
            "class",
            "import",
            "from",
            "None",
            "True",
            "False",
            "int",
            "float",
            "str",
            "bool",
        ]
        self.keyword_format = QTextCharFormat()
        self.keyword_format.setForeground(QColor("#005cc5"))
        self.keyword_format.setFontWeight(700)

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        for keyword in self.keywords:
            start = text.find(keyword)
            while start >= 0:
                before_ok = start == 0 or not text[start - 1].isalnum()
                end = start + len(keyword)
                after_ok = end >= len(text) or not text[end].isalnum()
                if before_ok and after_ok:
                    self.setFormat(start, len(keyword), self.keyword_format)
                start = text.find(keyword, start + 1)


class LineNumberArea(QWidget):
    def __init__(self, editor: "CodeEditor") -> None:
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self) -> QSize: # noqa: N802
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event) -> None:  # noqa: N802
        self.code_editor.line_number_area_paint_event(event)


class CodeEditor(QPlainTextEdit):
    def __init__(self) -> None:
        super().__init__()
        self.line_number_area = LineNumberArea(self)
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.update_line_number_area_width(0)
        self.highlight_current_line()
        self.highlighter = SimpleSyntaxHighlighter(self.document())

    def line_number_area_width(self) -> int:
        digits = len(str(max(1, self.blockCount())))
        return 10 + self.fontMetrics().horizontalAdvance("9") * digits

    def update_line_number_area_width(self, _new_block_count: int) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def line_number_area_paint_event(self, event) -> None:
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#f0f0f0"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#808080"))
                painter.drawText(
                    0,
                    top,
                    self.line_number_area.width() - 4,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    number,
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def highlight_current_line(self) -> None:
        if self.isReadOnly():
            return
        selection = QTextEdit.ExtraSelection()
        selection.format.setBackground(QColor("#fff8dc"))
        selection.format.setProperty(QTextCharFormat.Property.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        self.setExtraSelections([selection])


def build_editor_splitter() -> tuple[QSplitter, QTabWidget, QTabWidget, QTextEdit, QTableWidget]:
    editor_tabs = QTabWidget()
    editor_tabs.setTabsClosable(True)
    editor_tabs.setMovable(True)
    editor_tabs.setDocumentMode(True)

    output_tabs = QTabWidget()
    output_tabs.setMovable(True)
    output_tabs.setDocumentMode(True)

    output_log = QTextEdit()
    output_log.setReadOnly(True)
    output_log.setPlaceholderText("")

    output_errors = QTableWidget(0, 4)
    output_errors.setHorizontalHeaderLabels(["Неверный фрагмент", "Строка", "Позиция", "Сообщение"])

    output_tabs.addTab(output_log, "Лог")
    output_tabs.addTab(output_errors, "Ошибки")

    splitter = QSplitter(Qt.Orientation.Vertical)
    splitter.addWidget(editor_tabs)
    splitter.addWidget(output_tabs)
    splitter.setSizes([450, 220])
    splitter.setChildrenCollapsible(False)

    return splitter, editor_tabs, output_tabs, output_log, output_errors
