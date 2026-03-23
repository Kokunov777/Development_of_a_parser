from __future__ import annotations

import sys
from functools import partial
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QCloseEvent, QIcon, QKeySequence
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox, QStatusBar, QStyle, QToolBar, QTableWidget, QTableWidgetItem

from src.core.constants import ABOUT_TEXT, APP_TITLE, HELP_TEXT, TEXT_MENU_HINTS, TEXT_MENU_ITEMS
from src.core.file_service import read_text_file, write_text_file
from src.core.analyzer import scan_rust, Token, TokenType
from src.core.parser import parse_rust, SyntaxError as ParserSyntaxError
from src.ui.editor_widgets import CodeEditor, build_editor_splitter


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.language = "ru"
        self.setAcceptDrops(True)

        self.setWindowTitle(APP_TITLE)
        self.resize(1200, 760)
        self.setMinimumSize(900, 600)

        self._setup_central_area()
        self._setup_status_bar()
        self._setup_actions()
        self._setup_menu()
        self._setup_toolbar()
        self.new_file()

    def _setup_central_area(self) -> None:
        splitter, editor_tabs, output_tabs, output_log, output_errors = build_editor_splitter()
        self.editor_tabs = editor_tabs
        self.output_tabs = output_tabs
        self.output_log = output_log
        self.output_errors = output_errors
        self.setCentralWidget(splitter)

        # Таблица лексем
        self.output_tokens = QTableWidget(0, 4)
        self.output_tokens.setHorizontalHeaderLabels([
            "Условный код",
            "Тип лексемы",
            "Лексема",
            "Местоположение"
        ])
        self.output_tokens.setAlternatingRowColors(True)
        self.output_tokens.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.output_tokens.cellDoubleClicked.connect(self._jump_to_token)
        self.output_tabs.addTab(self.output_tokens, "Лексемы")

        self.editor_tabs.currentChanged.connect(lambda _: self._update_title())
        self.editor_tabs.tabCloseRequested.connect(self.close_editor_tab)
        self.output_errors.cellDoubleClicked.connect(self._jump_to_error)

    def _setup_status_bar(self) -> None:
        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("Готово")

    def _setup_actions(self) -> None:
        self.action_new = QAction("Создать", self)
        self.action_new.setIcon(self._icon("new.svg", QStyle.StandardPixmap.SP_FileIcon))
        self.action_new.setShortcut(QKeySequence.StandardKey.New)
        self.action_new.triggered.connect(self.new_file)

        self.action_open = QAction("Открыть", self)
        self.action_open.setIcon(self._icon("open.svg", QStyle.StandardPixmap.SP_DialogOpenButton))
        self.action_open.setShortcut(QKeySequence.StandardKey.Open)
        self.action_open.triggered.connect(self.open_file)

        self.action_save = QAction("Сохранить", self)
        self.action_save.setIcon(self._icon("save.svg", QStyle.StandardPixmap.SP_DialogSaveButton))
        self.action_save.setShortcut(QKeySequence.StandardKey.Save)
        self.action_save.triggered.connect(self.save_file)

        self.action_save_as = QAction("Сохранить как", self)
        self.action_save_as.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.action_save_as.triggered.connect(self.save_file_as)

        self.action_exit = QAction("Выход", self)
        self.action_exit.triggered.connect(self.close)

        self.action_undo = QAction("Отменить", self)
        self.action_undo.setIcon(self._icon("undo.svg", QStyle.StandardPixmap.SP_ArrowBack))
        self.action_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self.action_undo.triggered.connect(lambda: self._current_editor().undo() if self._current_editor() else None)

        self.action_redo = QAction("Повторить", self)
        self.action_redo.setIcon(self._icon("redo.svg", QStyle.StandardPixmap.SP_ArrowForward))
        self.action_redo.setShortcut(QKeySequence.StandardKey.Redo)
        self.action_redo.triggered.connect(lambda: self._current_editor().redo() if self._current_editor() else None)

        self.action_cut = QAction("Вырезать", self)
        self.action_cut.setIcon(self._icon("cut.svg", QStyle.StandardPixmap.SP_TrashIcon))
        self.action_cut.setShortcut(QKeySequence.StandardKey.Cut)
        self.action_cut.triggered.connect(lambda: self._current_editor().cut() if self._current_editor() else None)

        self.action_copy = QAction("Копировать", self)
        self.action_copy.setIcon(self._icon("copy.svg", QStyle.StandardPixmap.SP_FileLinkIcon))
        self.action_copy.setShortcut(QKeySequence.StandardKey.Copy)
        self.action_copy.triggered.connect(lambda: self._current_editor().copy() if self._current_editor() else None)

        self.action_paste = QAction("Вставить", self)
        self.action_paste.setIcon(self._icon("paste.svg", QStyle.StandardPixmap.SP_DialogApplyButton))
        self.action_paste.setShortcut(QKeySequence.StandardKey.Paste)
        self.action_paste.triggered.connect(lambda: self._current_editor().paste() if self._current_editor() else None)

        self.action_delete = QAction("Удалить", self)
        self.action_delete.triggered.connect(self.delete_selected_text)

        self.action_select_all = QAction("Выделить все", self)
        self.action_select_all.setShortcut(QKeySequence.StandardKey.SelectAll)
        self.action_select_all.triggered.connect(lambda: self._current_editor().selectAll() if self._current_editor() else None)

        self.action_start = QAction("Пуск", self)
        self.action_start.setShortcut(QKeySequence("F5"))
        self.action_start.triggered.connect(self.start_analyzer)

        self.action_help = QAction("Вызов справки", self)
        self.action_help.setIcon(self._icon("help.svg", QStyle.StandardPixmap.SP_DialogHelpButton))
        self.action_help.setShortcut(QKeySequence("F1"))
        self.action_help.triggered.connect(self.show_help)

        self.action_about = QAction("О программе", self)
        self.action_about.setIcon(self._icon("about.svg", QStyle.StandardPixmap.SP_MessageBoxInformation))
        self.action_about.triggered.connect(self.show_about)

        self.action_zoom_in = QAction("Увеличить текст", self)
        self.action_zoom_in.setShortcut(QKeySequence("Ctrl++"))
        self.action_zoom_in.triggered.connect(lambda: self._change_text_size(1))

        self.action_zoom_out = QAction("Уменьшить текст", self)
        self.action_zoom_out.setShortcut(QKeySequence("Ctrl+-"))
        self.action_zoom_out.triggered.connect(lambda: self._change_text_size(-1))

        self.action_zoom_reset = QAction("Сбросить размер текста", self)
        self.action_zoom_reset.setShortcut(QKeySequence("Ctrl+0"))
        self.action_zoom_reset.triggered.connect(self._reset_text_size)

        self.action_lang_ru = QAction("Русский", self)
        self.action_lang_ru.triggered.connect(lambda: self._switch_language("ru"))
        self.action_lang_en = QAction("English", self)
        self.action_lang_en.triggered.connect(lambda: self._switch_language("en"))

    def _setup_menu(self) -> None:
        menu_bar = self.menuBar()
        menu_bar.clear()

        self.menu_file = menu_bar.addMenu("Файл")
        self.menu_file.addAction(self.action_new)
        self.menu_file.addAction(self.action_open)
        self.menu_file.addAction(self.action_save)
        self.menu_file.addAction(self.action_save_as)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.action_exit)

        self.menu_edit = menu_bar.addMenu("Правка")
        self.menu_edit.addAction(self.action_undo)
        self.menu_edit.addAction(self.action_redo)
        self.menu_edit.addSeparator()
        self.menu_edit.addAction(self.action_cut)
        self.menu_edit.addAction(self.action_copy)
        self.menu_edit.addAction(self.action_paste)
        self.menu_edit.addAction(self.action_delete)
        self.menu_edit.addSeparator()
        self.menu_edit.addAction(self.action_select_all)
        self.menu_edit.addSeparator()
        self.menu_edit.addAction(self.action_zoom_in)
        self.menu_edit.addAction(self.action_zoom_out)
        self.menu_edit.addAction(self.action_zoom_reset)

        self.menu_text = menu_bar.addMenu("Текст")
        for item in TEXT_MENU_ITEMS:
            action = QAction(item, self)
            action.triggered.connect(partial(self.show_text_info, item))
            self.menu_text.addAction(action)

        menu_bar.addAction(self.action_start)

        self.menu_help = menu_bar.addMenu("Справка")
        self.menu_help.addAction(self.action_help)
        self.menu_help.addAction(self.action_about)

        self.menu_language = menu_bar.addMenu("Язык")
        self.menu_language.addAction(self.action_lang_ru)
        self.menu_language.addAction(self.action_lang_en)

    def _setup_toolbar(self) -> None:
        toolbar = QToolBar("Панель инструментов", self)
        toolbar.setMovable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        self.addToolBar(toolbar)
        toolbar.addAction(self.action_new)
        toolbar.addAction(self.action_open)
        toolbar.addAction(self.action_save)
        toolbar.addSeparator()
        toolbar.addAction(self.action_start)
        toolbar.addSeparator()
        toolbar.addAction(self.action_undo)
        toolbar.addAction(self.action_redo)
        toolbar.addSeparator()
        toolbar.addAction(self.action_copy)
        toolbar.addAction(self.action_cut)
        toolbar.addAction(self.action_paste)
        toolbar.addSeparator()
        toolbar.addAction(self.action_help)
        toolbar.addAction(self.action_about)

    def _new_editor(self, text: str = "", title: str = "Без имени", file_path: str | None = None) -> None:
        editor = CodeEditor()
        editor.setPlainText(text)
        editor.setProperty("file_path", file_path)
        editor.document().setModified(False)
        editor.document().modificationChanged.connect(lambda _: self._refresh_current_tab_text())
        index = self.editor_tabs.addTab(editor, title)
        self.editor_tabs.setCurrentIndex(index)
        self._update_title()

    def _current_editor(self) -> CodeEditor | None:
        widget = self.editor_tabs.currentWidget()
        return widget if isinstance(widget, CodeEditor) else None

    def _current_file_path(self) -> str | None:
        editor = self._current_editor()
        if not editor:
            return None
        return editor.property("file_path")

    def _set_current_file_path(self, file_path: str | None) -> None:
        editor = self._current_editor()
        if editor:
            editor.setProperty("file_path", file_path)

    def _refresh_current_tab_text(self) -> None:
        editor = self._current_editor()
        if not editor:
            return
        file_path = editor.property("file_path")
        name = Path(file_path).name if file_path else "Без имени"
        mark = "*" if editor.document().isModified() else ""
        self.editor_tabs.setTabText(self.editor_tabs.currentIndex(), f"{name}{mark}")
        self._update_title()

    def _icon(self, icon_name: str, fallback: QStyle.StandardPixmap) -> QIcon:
        icon_path = self._resource_path(Path("assets") / "icons" / icon_name)
        if icon_path.exists():
            return QIcon(str(icon_path))
        return self.style().standardIcon(fallback)

    @staticmethod
    def _resource_path(relative_path: Path) -> Path:
        if getattr(sys, "_MEIPASS", None):
            return Path(sys._MEIPASS) / relative_path
        return Path(__file__).resolve().parents[2] / relative_path

    def _set_output(self, text: str) -> None:
        self.output_log.setPlainText(text)
        self.output_tabs.setCurrentWidget(self.output_log)

    @staticmethod
    def _report_code(prefix: str, text: str) -> str:
        value = sum(ord(ch) for ch in text) % 10000000000
        return f"{prefix}{value}"

    def _update_title(self) -> None:
        path = self._current_file_path()
        name = Path(path).name if path else "Без имени"
        editor = self._current_editor()
        mark = "*" if editor and editor.document().isModified() else ""
        self.setWindowTitle(f"{APP_TITLE} - {name}{mark}")
        self.statusBar().showMessage(f"Вкладок: {self.editor_tabs.count()} | Файл: {name}")

    def _ask_save_editor(self, editor: CodeEditor) -> bool:
        if not editor.document().isModified():
            return True
        result = QMessageBox.question(
            self,
            "Несохраненные изменения",
            "Документ был изменен. Сохранить изменения?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes,
        )
        if result == QMessageBox.StandardButton.Cancel:
            return False
        if result == QMessageBox.StandardButton.Yes:
            current = self.editor_tabs.currentWidget()
            self.editor_tabs.setCurrentWidget(editor)
            ok = self.save_file()
            self.editor_tabs.setCurrentWidget(current)
            return ok
        return True

    def new_file(self) -> None:
        self._new_editor()
        self._set_output("Создан новый документ.")

    def open_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Открыть файл", "", "Text files (*.txt);;All files (*.*)")
        if file_path:
            self._open_file_path(file_path)

    def _open_file_path(self, file_path: str) -> None:
        try:
            content = read_text_file(file_path)
        except OSError as error:
            QMessageBox.critical(self, "Ошибка", f"Не удалось открыть файл:\n{error}")
            return
        self._new_editor(content, Path(file_path).name, file_path)
        self._set_output(f"Файл открыт:\n{file_path}")

    def save_file(self) -> bool:
        editor = self._current_editor()
        if not editor:
            return False
        path = editor.property("file_path")
        if not path:
            return self.save_file_as()
        try:
            write_text_file(path, editor.toPlainText())
        except OSError as error:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл:\n{error}")
            return False
        editor.document().setModified(False)
        self._refresh_current_tab_text()
        self._set_output(f"Файл сохранен:\n{path}")
        return True

    def save_file_as(self) -> bool:
        editor = self._current_editor()
        if not editor:
            return False
        file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить файл как", "", "Text files (*.txt);;All files (*.*)")
        if not file_path:
            return False
        self._set_current_file_path(file_path)
        return self.save_file()

    def delete_selected_text(self) -> None:
        editor = self._current_editor()
        if not editor:
            return
        cursor = editor.textCursor()
        if cursor.hasSelection():
            cursor.removeSelectedText()
            editor.setTextCursor(cursor)

    def start_analyzer(self) -> None:
        editor = self._current_editor()
        if not editor:
            return
        text = editor.toPlainText()
        self.output_errors.setRowCount(0)
        self.output_tokens.setRowCount(0)
        if not text.strip():
            self._set_output("Пуск: текст пуст. Добавьте данные для анализа.")
            return

        tokens, errors = scan_rust(text)

       
        russian_names = {
            TokenType.KEYWORD: "Ключевое слово",
            TokenType.IDENTIFIER: "Идентификатор",
            TokenType.OPERATOR: "Оператор",
            TokenType.COLON: "Двоеточие",
            TokenType.DOT: "Точка",
            TokenType.INTEGER: "Целое число",
            TokenType.FLOAT: "Вещественное число",
            TokenType.SEPARATOR: "Разделитель",
            TokenType.END_OF_STATEMENT: "Конец оператора",
            TokenType.WHITESPACE: "Разделитель пробел",
            TokenType.ERROR: "Ошибка",
        }

       
        def visible_lexeme(lexeme: str) -> str:
           
            replacements = {
                ' ': 'пробел',
                '\t': '\\t',
                '\r': '\\r',
                '\n': '\\n',
            }
            result = []
            for ch in lexeme:
                if ch in replacements:
                    result.append(replacements[ch])
                else:
                    result.append(ch)
            return ''.join(result)

       
        for token in tokens:
            row = self.output_tokens.rowCount()
            self.output_tokens.insertRow(row)
            self.output_tokens.setItem(row, 0, QTableWidgetItem(str(token.type.value)))
            type_name = russian_names.get(token.type, token.type.name)
            self.output_tokens.setItem(row, 1, QTableWidgetItem(type_name))
            self.output_tokens.setItem(row, 2, QTableWidgetItem(visible_lexeme(token.lexeme)))
            location = f"{token.start_line}:{token.start_col}-{token.end_line}:{token.end_col}"
            self.output_tokens.setItem(row, 3, QTableWidgetItem(location))

        
        # Лексические ошибки
        for err in errors:
            row = self.output_errors.rowCount()
            self.output_errors.insertRow(row)
            # Неверный фрагмент (извлекаем из сообщения или оставляем пустым)
            fragment = err.message.split("'")[1] if "'" in err.message else "?"
            self.output_errors.setItem(row, 0, QTableWidgetItem(fragment))
            self.output_errors.setItem(row, 1, QTableWidgetItem(str(err.line)))
            self.output_errors.setItem(row, 2, QTableWidgetItem(str(err.column)))
            self.output_errors.setItem(row, 3, QTableWidgetItem(err.message))

        # Синтаксический анализ
        syntax_errors = parse_rust(tokens)
        for serr in syntax_errors:
            row = self.output_errors.rowCount()
            self.output_errors.insertRow(row)
            fragment = serr.token.lexeme if serr.token else "?"
            self.output_errors.setItem(row, 0, QTableWidgetItem(fragment))
            self.output_errors.setItem(row, 1, QTableWidgetItem(str(serr.line)))
            self.output_errors.setItem(row, 2, QTableWidgetItem(str(serr.column)))
            self.output_errors.setItem(row, 3, QTableWidgetItem(serr.message))

        total_errors = len(errors) + len(syntax_errors)
        if tokens:
            self.output_tabs.setCurrentWidget(self.output_tokens)
        elif total_errors > 0:
            self.output_tabs.setCurrentWidget(self.output_errors)
            self._set_output(f"Найдено ошибок: {total_errors}")
        else:
            self._set_output("Лексемы не обнаружены.")

    def _tbl_item(self, text: str):
        from PySide6.QtWidgets import QTableWidgetItem

        return QTableWidgetItem(text)

    def _jump_to_error(self, row: int, _col: int) -> None:
        editor = self._current_editor()
        if not editor:
            return
        line_item = self.output_errors.item(row, 1)  # колонка "Строка"
        pos_item = self.output_errors.item(row, 2)   # колонка "Позиция"
        if not line_item or not pos_item:
            return
        line = max(1, int(line_item.text()))
        pos = max(1, int(pos_item.text()))
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.MoveAnchor, line - 1)
        cursor.movePosition(cursor.MoveOperation.Right, cursor.MoveMode.MoveAnchor, pos - 1)
        editor.setTextCursor(cursor)
        editor.setFocus()

    def _jump_to_token(self, row: int, _col: int) -> None:
        editor = self._current_editor()
        if not editor:
            return
        location_item = self.output_tokens.item(row, 3)
        if not location_item:
            return
        location = location_item.text()
        import re
        match = re.match(r"(\d+):(\d+)-(\d+):(\d+)", location)
        if not match:
            return
        start_line, start_col, end_line, end_col = map(int, match.groups())
        cursor = editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.MoveAnchor, start_line - 1)
        cursor.movePosition(cursor.MoveOperation.Right, cursor.MoveMode.MoveAnchor, start_col - 1)
       
        end_cursor = editor.textCursor()
        end_cursor.movePosition(cursor.MoveOperation.Start)
        end_cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.MoveAnchor, end_line - 1)
        end_cursor.movePosition(cursor.MoveOperation.Right, cursor.MoveMode.MoveAnchor, end_col - 1)
        cursor.setPosition(end_cursor.position(), cursor.MoveMode.KeepAnchor)
        editor.setTextCursor(cursor)
        editor.setFocus()

    def show_help(self) -> None:
        QMessageBox.information(self, "Справка", HELP_TEXT)

    def show_about(self) -> None:
        QMessageBox.information(self, "О программе", ABOUT_TEXT)

    def show_text_info(self, item_name: str) -> None:
        QMessageBox.information(self, item_name, TEXT_MENU_HINTS[item_name])

    def close_editor_tab(self, index: int) -> None:
        widget = self.editor_tabs.widget(index)
        if isinstance(widget, CodeEditor) and not self._ask_save_editor(widget):
            return
        self.editor_tabs.removeTab(index)
        if self.editor_tabs.count() == 0:
            self.new_file()
        self._update_title()

    def _change_text_size(self, step: int) -> None:
        editor = self._current_editor()
        if editor:
            editor.zoomIn(step)
        self.output_log.zoomIn(step)

    def _reset_text_size(self) -> None:
        for widget in [self._current_editor(), self.output_log]:
            if widget:
                font = widget.font()
                font.setPointSize(10)
                widget.setFont(font)

    def _switch_language(self, lang: str) -> None:
        self.language = lang
        if lang == "en":
            self.menu_file.setTitle("File")
            self.menu_edit.setTitle("Edit")
            self.menu_text.setTitle("Text")
            self.menu_help.setTitle("Help")
            self.menu_language.setTitle("Language")
            self.statusBar().showMessage("Language switched to English", 3000)
        else:
            self.menu_file.setTitle("Файл")
            self.menu_edit.setTitle("Правка")
            self.menu_text.setTitle("Текст")
            self.menu_help.setTitle("Справка")
            self.menu_language.setTitle("Язык")
            self.statusBar().showMessage("Язык переключен на русский", 3000)

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        for url in event.mimeData().urls():
            local = url.toLocalFile()
            if local and Path(local).is_file():
                self._open_file_path(local)
        event.acceptProposedAction()

    def closeEvent(self, event: QCloseEvent) -> None:
        for i in range(self.editor_tabs.count()):
            editor = self.editor_tabs.widget(i)
            if isinstance(editor, CodeEditor) and not self._ask_save_editor(editor):
                event.ignore()
                return
        event.accept()
