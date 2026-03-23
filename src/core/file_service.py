from pathlib import Path


def read_text_file(path: str) -> str:
    file_path = Path(path)
    try:
        return file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return file_path.read_text(encoding="cp1251")


def write_text_file(path: str, data: str) -> None:
    Path(path).write_text(data, encoding="utf-8")
