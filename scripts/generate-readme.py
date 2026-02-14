"""Stitch multiple markdown files into a single README."""

import sys
from pathlib import Path


def stitch_markdown_files(markdown_files: list[str], output_file: str = "README.md") -> None:
    combined_content = []

    for file in markdown_files:
        path = Path(file)
        if not path.exists():
            print(f"File not found: {file}")
            sys.exit(1)

        content = path.read_text(encoding="utf-8").strip()
        combined_content.append(content)

    Path(output_file).write_text("\n\n".join(combined_content) + "\n", encoding="utf-8")

    print(f"{output_file} successfully created with {len(markdown_files)} sections.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate-readme.py file1.md file2.md ... [fileN.md]")
        sys.exit(1)

    input_files = sys.argv[1:]
    stitch_markdown_files(input_files)
