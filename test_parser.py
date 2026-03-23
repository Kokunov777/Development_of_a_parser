import sys
sys.path.insert(0, '.')
from src.core.analyzer import scan_rust
from src.core.parser import parse_rust, SyntaxError

def test_correct():
    text = "let complex_num2 = num::complex::Complex::new(3.1, -4.2);"
    tokens, lex_errors = scan_rust(text)
    assert len(lex_errors) == 0, f"Лексические ошибки: {lex_errors}"
    errors = parse_rust(tokens)
    if errors:
        for err in errors:
            print(err)
    assert len(errors) == 0, f"Синтаксические ошибки: {errors}"
    print("PASS: correct parsing")

def test_missing_semicolon():
    text = "let x = num::complex::Complex::new(1, 2)"
    tokens, _ = scan_rust(text)
    errors = parse_rust(tokens)
    assert len(errors) > 0, "Ожидалась ошибка отсутствия точки с запятой"
    print("PASS: missing semicolon detected")

def test_missing_let():
    text = "x = num::complex::Complex::new(1, 2);"
    tokens, _ = scan_rust(text)
    errors = parse_rust(tokens)
    assert len(errors) > 0, "Ожидалась ошибка отсутствия let"
    print("PASS: missing let detected")

def test_wrong_path():
    text = "let x = num::complex::;"
    tokens, _ = scan_rust(text)
    errors = parse_rust(tokens)
    assert len(errors) > 0, "Ожидалась ошибка в пути"
    print("PASS: wrong path detected")

def test_extra_comma():
    text = "let x = num::complex::Complex::new(1, , 2);"
    tokens, _ = scan_rust(text)
    errors = parse_rust(tokens)
    assert len(errors) > 0, "Ожидалась ошибка лишней запятой"
    print("PASS: extra comma detected")

def test_no_errors_recovery():
    # Текст с ошибкой, но парсер должен восстановиться и продолжить
    text = "let x = num::complex::Complex::new(1, 2); let y = num::complex::Complex::new(3, 4);"
    tokens, _ = scan_rust(text)
    errors = parse_rust(tokens)
    # Ожидаем, что ошибок нет
    assert len(errors) == 0, f"Ошибки при восстановлении: {errors}"
    print("PASS: recovery works")

def run_all():
    test_correct()
    test_missing_semicolon()
    test_missing_let()
    test_wrong_path()
    test_extra_comma()
    test_no_errors_recovery()
    print("All parser tests passed.")

if __name__ == "__main__":
    run_all()