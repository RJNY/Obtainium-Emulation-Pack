import sys
import os


def stitch_markdown_files(init_file, table_file, faq_file, output_file="README.md"):
    files = [init_file, table_file, faq_file]
    combined_content = []

    for file in files:
        if not os.path.exists(file):
            print(f"❌ File not found: {file}")
            sys.exit(1)

        with open(file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            combined_content.append(content)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n\n".join(combined_content) + "\n")

    print(f"✅ README.md successfully created with {len(files)} sections.")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python stitch_markdown.py init.md table.md faq.md")
        sys.exit(1)

    stitch_markdown_files(sys.argv[1], sys.argv[2], sys.argv[3])
