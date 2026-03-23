from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
from .analyzer import Token, TokenType, LexerError


@dataclass
class SyntaxError:
    """Ошибка синтаксического анализа."""
    token: Optional[Token]  # Токен, на котором обнаружена ошибка (может быть None)
    message: str
    # Позиции для удобства
    line: int
    column: int

    def __str__(self) -> str:
        return f"Синтаксическая ошибка в {self.line}:{self.column}: {self.message}"


class Parser:
    """Синтаксический анализатор для грамматики объявления комплексных чисел."""

    def __init__(self, tokens: List[Token]) -> None:
        # Фильтруем пробелы и ошибки лексического анализа
        self.tokens = [t for t in tokens if t.type not in (TokenType.WHITESPACE, TokenType.ERROR)]
        self.pos = 0  # текущая позиция в списке токенов
        self.errors: List[SyntaxError] = []
        self.sync_tokens = {TokenType.END_OF_STATEMENT, TokenType.KEYWORD}  # для восстановления

    def current_token(self) -> Optional[Token]:
        """Возвращает текущий токен или None, если достигнут конец."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def peek(self, offset: int = 0) -> Optional[Token]:
        """Возвращает токен на заданном смещении от текущей позиции."""
        idx = self.pos + offset
        if idx < len(self.tokens):
            return self.tokens[idx]
        return None

    def consume(self, expected_type: Optional[TokenType] = None, lexeme: Optional[str] = None) -> Optional[Token]:
        """
        Потребляет текущий токен, если он соответствует ожидаемому типу и/то лексеме.
        Если не соответствует, регистрирует ошибку и пытается восстановиться.
        Возвращает потреблённый токен или None.
        """
        token = self.current_token()
        if token is None:
            self._error_expected(expected_type, lexeme)
            return None
        if expected_type is not None and token.type != expected_type:
            self._error_expected(expected_type, lexeme, token)
            self._sync()
            return None
        if lexeme is not None and token.lexeme != lexeme:
            self._error_expected(expected_type, lexeme, token)
            self._sync()
            return None
        # Совпадение
        self.pos += 1
        return token

    def _error_expected(self, expected_type: Optional[TokenType], expected_lexeme: Optional[str],
                        actual: Optional[Token] = None) -> None:
        """Регистрирует ошибку 'ожидался X, но получен Y'."""
        if actual is None:
            actual = self.current_token()
        if actual is None:
            pos = "конец файла"
            line = 1
            col = 1
        else:
            pos = f"{actual.start_line}:{actual.start_col}"
            line = actual.start_line
            col = actual.start_col
        expected = []
        if expected_type:
            expected.append(f"тип {expected_type.name}")
        if expected_lexeme:
            expected.append(f"лексема '{expected_lexeme}'")
        expected_str = " или ".join(expected) if expected else "что-то"
        msg = f"Ожидался {expected_str}, но получен {actual.lexeme if actual else 'конец файла'} на позиции {pos}"
        self.errors.append(SyntaxError(actual, msg, line, col))

    def _sync(self) -> None:
        """Восстановление после ошибки: пропускаем токены до синхронизирующего."""
        while self.current_token() is not None:
            if self.current_token().type in self.sync_tokens:
                break
            self.pos += 1

    def parse(self) -> List[SyntaxError]:
        """
        Запускает синтаксический анализ.
        Возвращает список ошибок (пустой, если анализ успешен).
        """
        self.errors.clear()
        self.pos = 0
        try:
            self._program()
        except Exception as e:
            # Неожиданная ошибка - добавляем в список
            self.errors.append(SyntaxError(None, f"Внутренняя ошибка парсера: {e}", 1, 1))
        return self.errors

    def _program(self) -> None:
        """program := declaration"""
        while self.current_token() is not None:
            self._declaration()

    def _declaration(self) -> None:
        """declaration := 'let' identifier '=' expression ';'"""
        # 'let'
        if not self.consume(TokenType.KEYWORD, "let"):
            return
        # identifier
        if not self.consume(TokenType.IDENTIFIER):
            return
        # '='
        if not self.consume(TokenType.OPERATOR, "="):
            return
        # expression
        self._expression()
        # ';'
        self.consume(TokenType.END_OF_STATEMENT, ";")

    def _expression(self) -> None:
        """expression := path '::' 'new' '(' arguments ')'"""
        # path
        self._path()
        # '::' - два токена COLON подряд
        if not (self.consume(TokenType.COLON, ":") and self.consume(TokenType.COLON, ":")):
            self._error_expected(None, "::")
            return
        # 'new'
        if not self.consume(TokenType.IDENTIFIER, "new"):
            # Может быть ключевым словом? У нас new это идентификатор.
            # Но в грамматике это ключевое слово, однако лексер не выделяет его отдельно.
            # Поэтому проверяем как идентификатор с лексемой 'new'.
            return
        # '('
        if not self.consume(TokenType.SEPARATOR, "("):
            return
        # arguments
        self._arguments()
        # ')'
        self.consume(TokenType.SEPARATOR, ")")

    def _path(self) -> None:
        """path := identifier ('::' identifier)*, но останавливается перед '::' если следующий идентификатор 'new'."""
        # identifier
        if not self.consume(TokenType.IDENTIFIER):
            return
        while True:
            # Проверяем два впереди идущих COLON
            if not (self.peek() is not None and self.peek().type == TokenType.COLON and
                    self.peek(1) is not None and self.peek(1).type == TokenType.COLON):
                break
            # Проверяем, что после '::' не следует 'new'
            if self.peek(2) is not None and self.peek(2).type == TokenType.IDENTIFIER and self.peek(2).lexeme == "new":
                break
            # Потребляем '::' и следующий идентификатор
            self.consume(TokenType.COLON, ":")
            self.consume(TokenType.COLON, ":")
            if not self.consume(TokenType.IDENTIFIER):
                break

    def _arguments(self) -> None:
        """arguments := number (',' number)*"""
        # number
        self._number()
        # повторяем (',' number)
        while self.peek() is not None and self.peek().type == TokenType.SEPARATOR and self.peek().lexeme == ",":
            self.consume(TokenType.SEPARATOR, ",")
            self._number()

    def _number(self) -> None:
        """number := INTEGER | FLOAT"""
        token = self.current_token()
        if token is None:
            self._error_expected(None, "число")
            return
        if token.type not in (TokenType.INTEGER, TokenType.FLOAT):
            self._error_expected(TokenType.INTEGER, None, token)
            self._sync()
            return
        self.consume(token.type)  # потребляем число


def parse_rust(tokens: List[Token]) -> List[SyntaxError]:
    """Удобная функция для синтаксического анализа."""
    parser = Parser(tokens)
    return parser.parse()