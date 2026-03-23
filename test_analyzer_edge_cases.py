import sys
sys.path.insert(0, '.')
from src.core.analyzer import scan_rust, TokenType

def test_integer_with_leading_zero():
    text = "let x = 012;"
    tokens, errors = scan_rust(text)
    # 012 должно быть распознано как INTEGER "012"
    int_tokens = [t for t in tokens if t.type == TokenType.INTEGER]
    assert len(int_tokens) == 1
    assert int_tokens[0].lexeme == "012"
    print("PASS: integer with leading zero")

def test_float_starting_with_dot():
    text = "let x = .5;"
    tokens, errors = scan_rust(text)
    # .5 должно быть распознано как FLOAT ".5"? У нас нет правила для точки в начале числа.
    # Сканер увидит '.' как DOT, затем '5' как INTEGER.
    # Это ожидаемое поведение, проверим.
    dot_tokens = [t for t in tokens if t.type == TokenType.DOT]
    int_tokens = [t for t in tokens if t.type == TokenType.INTEGER]
    assert len(dot_tokens) == 1
    assert dot_tokens[0].lexeme == "."
    assert len(int_tokens) == 1
    assert int_tokens[0].lexeme == "5"
    print("PASS: dot before number")

def test_float_ending_with_dot():
    text = "let x = 5.;"
    tokens, errors = scan_rust(text)
    # 5. должно быть распознано как INTEGER "5" и DOT "."? Или как FLOAT "5."?
    # Согласно логике сканера, точка будет включена в число, но затем откатана.
    # Поэтому будет INTEGER "5" и DOT "."? Проверим.
    int_tokens = [t for t in tokens if t.type == TokenType.INTEGER]
    dot_tokens = [t for t in tokens if t.type == TokenType.DOT]
    # Ожидаем INTEGER "5" и DOT "."
    assert len(int_tokens) == 1
    assert int_tokens[0].lexeme == "5"
    assert len(dot_tokens) == 1
    assert dot_tokens[0].lexeme == "."
    print("PASS: number ending with dot")

def test_negative_with_space():
    text = "let x = - 5;"
    tokens, errors = scan_rust(text)
    # '-' будет недопустимым символом? Нет, он будет распознан как начало числа, но после пробела цифра.
    # Сканер увидит '-' как отдельный символ, который не является оператором, поэтому ошибка.
    # Проверим наличие ошибки.
    assert len(errors) == 1
    print("PASS: negative with space causes error")

def test_identifier_with_underscore():
    text = "_var = 42"
    tokens, errors = scan_rust(text)
    ident_tokens = [t for t in tokens if t.type == TokenType.IDENTIFIER]
    assert len(ident_tokens) == 1
    assert ident_tokens[0].lexeme == "_var"
    print("PASS: identifier with underscore")

def test_multiple_operators():
    text = "x = y"
    tokens, errors = scan_rust(text)
    op_tokens = [t for t in tokens if t.type == TokenType.OPERATOR]
    assert len(op_tokens) == 1
    assert op_tokens[0].lexeme == "="
    print("PASS: single operator")

def test_invalid_characters():
    text = "let x = @#"
    tokens, errors = scan_rust(text)
    assert len(errors) == 2  # @ и #
    print("PASS: invalid characters detected")

def run_all():
    test_integer_with_leading_zero()
    test_float_starting_with_dot()
    test_float_ending_with_dot()
    test_negative_with_space()
    test_identifier_with_underscore()
    test_multiple_operators()
    test_invalid_characters()
    print("All edge case tests passed.")

if __name__ == "__main__":
    run_all()