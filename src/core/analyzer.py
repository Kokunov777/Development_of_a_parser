import re
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Optional


class TokenType(Enum):
    KEYWORD = 1          # let
    IDENTIFIER = 2       # complex_num2, num, complex, Complex, new
    OPERATOR = 3         # =
    COLON = 4            # :
    DOT = 5              # .
    INTEGER = 6          # 42, -5
    FLOAT = 7            # 3.1, -4.2, 0.5
    SEPARATOR = 8        # ( ) ,
    END_OF_STATEMENT = 9 # ;
    WHITESPACE = 10      # пробелы, табы, возврат каретки
    ERROR = 11           # недопустимый символ


@dataclass
class Token:
    type: TokenType
    lexeme: str
    start_line: int
    start_col: int
    end_line: int
    end_col: int


@dataclass
class LexerError:
    line: int
    column: int
    message: str


class RustScanner:
    """
    Лексический анализатор для Rust-подобного синтаксиса (ограниченный объявлением комплексных чисел).
    Обрабатывает текст, разбивая его на токены и собирая ошибки.
    """
    def __init__(self):
        self.tokens: List[Token] = []
        self.errors: List[LexerError] = []
        self.line = 1
        self.col = 1
        self.i = 0
        self.text = ""
        self.n = 0
    
    def analyze(self, text: str) -> Tuple[List[Token], List[LexerError]]:
        """
        Основной метод анализа текста.
        Возвращает список токенов и список ошибок лексического анализа.
        """
        self.text = text
        self.n = len(text)
        self.tokens.clear()
        self.errors.clear()
        self.line = 1
        self.col = 1
        self.i = 0
        
        while self.i < self.n:
            self._process_next()
        
        return self.tokens, self.errors
    
    def _process_next(self):
        ch = self.text[self.i]
        start_line = self.line
        start_col = self.col
        
 
        if ch == '\n':
            self.line += 1
            self.col = 1
            self.i += 1
            return
        
  
        if ch in ' \t\r':
            j = self.i
            while j < self.n and self.text[j] in ' \t\r':
                j += 1
            lexeme = self.text[self.i:j]
            self.tokens.append(Token(TokenType.WHITESPACE, lexeme, start_line, start_col, self.line, self.col + (j - self.i) - 1))
            self.col += j - self.i
            self.i = j
            return
        
 
        if ch == 'l' and self.i + 2 < self.n and self.text[self.i:self.i+3] == 'let' and (self.i + 3 == self.n or not self.text[self.i+3].isalnum()):
            self.tokens.append(Token(TokenType.KEYWORD, 'let', start_line, start_col, self.line, self.col + 2))
            self.i += 3
            self.col += 3
            return
  
        if ch.isalpha() or ch == '_':
            j = self.i
            while j < self.n and (self.text[j].isalnum() or self.text[j] == '_'):
                j += 1
            lexeme = self.text[self.i:j]
            self.tokens.append(Token(TokenType.IDENTIFIER, lexeme, start_line, start_col, self.line, self.col + (j - self.i) - 1))
            self.col += j - self.i
            self.i = j
            return
        

        if ch.isdigit() or (ch == '-' and self.i + 1 < self.n and self.text[self.i+1].isdigit()):
            j = self.i
            if ch == '-':
                j += 1
            has_dot = False
            while j < self.n and (self.text[j].isdigit() or (self.text[j] == '.' and not has_dot)):
                if self.text[j] == '.':
                    has_dot = True
                j += 1
           
            if has_dot and j > self.i + 1 and self.text[j-1] == '.':
                j -= 1  
                has_dot = False  
            lexeme = self.text[self.i:j]
            token_type = TokenType.FLOAT if has_dot else TokenType.INTEGER
            self.tokens.append(Token(token_type, lexeme, start_line, start_col, self.line, self.col + (j - self.i) - 1))
            self.col += j - self.i
            self.i = j
            return
    
        if ch == '=':
            self.tokens.append(Token(TokenType.OPERATOR, '=', start_line, start_col, self.line, self.col))
            self.i += 1
            self.col += 1
            return
        
     
        if ch == ':':
            self.tokens.append(Token(TokenType.COLON, ':', start_line, start_col, self.line, self.col))
            self.i += 1
            self.col += 1
            return
        
        
        if ch == '.':
            self.tokens.append(Token(TokenType.DOT, '.', start_line, start_col, self.line, self.col))
            self.i += 1
            self.col += 1
            return
    
        if ch in '(),;':
            token_type = TokenType.END_OF_STATEMENT if ch == ';' else TokenType.SEPARATOR
            self.tokens.append(Token(token_type, ch, start_line, start_col, self.line, self.col))
            self.i += 1
            self.col += 1
            return
        
     
        self.errors.append(LexerError(self.line, self.col, f"Недопустимый символ '{ch}'"))
        self.i += 1
        self.col += 1


def scan_rust(text: str) -> Tuple[List[Token], List[LexerError]]:
    """
    Лексический анализатор для Rust (ограниченный объявлением комплексных чисел).
    Возвращает список токенов и список ошибок.
    """
    scanner = RustScanner()
    return scanner.analyze(text)


def _analyze_rust(text: str) -> list[tuple[int, int, str]]:
    """
    Анализ Rust текста, возвращает ошибки в формате (строка, колонка, сообщение).
    """
    _, errors = scan_rust(text)
    return [(err.line, err.column, err.message) for err in errors]


def analyze_text(language: str, text: str) -> list[tuple[int, int, str]]:
    if language == "python":
        return _analyze_python(text)
    if language == "rust":
        return _analyze_rust(text)
    return _analyze_c_like(language, text)


def _analyze_python(text: str) -> list[tuple[int, int, str]]:
    try:
        compile(text, "<editor>", "exec")
        return []
    except SyntaxError as error:
        line = error.lineno or 1
        col = error.offset or 1
        return [(line, col, error.msg or "Syntax error")]


def _analyze_c_like(language: str, text: str) -> list[tuple[int, int, str]]:
    errors: list[tuple[int, int, str]] = []
    types_map = {
        "c": {"int", "float", "double", "char", "long", "short", "void", "bool"},
        "c++": {"int", "float", "double", "char", "long", "short", "void", "bool", "auto", "string"},
        "c#": {"int", "float", "double", "char", "long", "short", "void", "bool", "string", "var", "decimal"},
        "rust": {"i8", "i16", "i32", "i64", "u8", "u16", "u32", "u64", "f32", "f64", "bool", "char", "String", "usize"},
    }
    known_types = types_map.get(language, set())

    for i, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("//") or line in {"{", "}"}:
            continue

        if not line.endswith(";") and not line.endswith("{") and not line.endswith("}"):
            errors.append((i, len(raw_line), "Отсутствует ';' в конце оператора"))

        tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\S", line)
        if not tokens:
            continue

        if tokens[0] in known_types:
            if len(tokens) < 2:
                errors.append((i, 1, "Отсутствует идентификатор после типа"))
                continue
            ident = tokens[1]
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", ident):
                col = max(1, raw_line.find(ident) + 1)
                errors.append((i, col, f"Неверный идентификатор '{ident}'"))
            if len(tokens) > 2 and tokens[2] not in {"=", ";"}:
                col = max(1, raw_line.find(tokens[2]) + 1)
                errors.append((i, col, "Неверное задание константы"))

        bad_number_ident = re.search(r"\b\d+[A-Za-z_]+\w*\b", line)
        if bad_number_ident:
            errors.append((i, bad_number_ident.start() + 1, "Неверное задание константы"))

    return errors
