import sys
sys.path.insert(0, '.')
from src.core.analyzer import scan_rust, TokenType

def test_whitespace():
    text = "let  x = 5;"
    tokens, errors = scan_rust(text)
    print(f"Tokens count: {len(tokens)}")
    for token in tokens:
        print(f"  {token.type.name:15} '{token.lexeme}' {token.start_line}:{token.start_col}-{token.end_line}:{token.end_col}")
    whitespace_tokens = [t for t in tokens if t.type == TokenType.WHITESPACE]
    print(f"Whitespace tokens: {len(whitespace_tokens)}")
    for wt in whitespace_tokens:
        print(f"  '{wt.lexeme}'")
    assert len(whitespace_tokens) > 0
    print("Whitespace test passed.")

if __name__ == "__main__":
    test_whitespace()