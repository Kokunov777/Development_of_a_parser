import sys
sys.path.insert(0, '.')
from src.core.analyzer import scan_rust

def test_errors():
    text = "let x = @;"
    tokens, errors = scan_rust(text)
    print(f"Tokens: {len(tokens)}, Errors: {len(errors)}")
    for err in errors:
        print(f"  {err.line}:{err.column} {err.message}")
    assert len(errors) == 1
    assert errors[0].message.startswith("Недопустимый символ")
    print("Error test passed.")

if __name__ == "__main__":
    test_errors()