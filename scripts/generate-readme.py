import sys
import os


def stitch_markdown_files(markdown_files, output_file="README.md"):
    combined_content = []

    for file in markdown_files:
        if not os.path.exists(file):
            print(f"❌ File not found: {file}")
            sys.exit(1)

        with open(file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            combined_content.append(content)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n\n".join(combined_content) + "\n")

    print(f"✅ {output_file} successfully created with {len(markdown_files)} sections.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate-readme.py file1.md file2.md ... [fileN.md]")
        sys.exit(1)

    input_files = sys.argv[1:]
    stitch_markdown_files(input_files)
