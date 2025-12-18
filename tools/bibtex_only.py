import re
from pathlib import Path

DEFAULT_INPUT = "ai-paper-finder.info search results.txt"
DEFAULT_OUTPUT = "references.bib"


def extract_bibtex_entries(input_path, output_path):
    text = Path(input_path).read_text(encoding="utf-8")

    bibtex_blocks = re.findall(
        r"BibTeX:\s*\n(@[\s\S]*?\n})",
        text,
        flags=re.MULTILINE
    )

    if not bibtex_blocks:
        raise ValueError("No BibTeX entries found in the input file.")

    clean_bibtex = "\n\n".join(block.strip() for block in bibtex_blocks)

    Path(output_path).write_text(clean_bibtex + "\n", encoding="utf-8")

    print(f"Extracted {len(bibtex_blocks)} BibTeX entries.")
    print(f"Production-ready BibTeX written to: {output_path}")


def main():
    print(f"Default input file: '{DEFAULT_INPUT}'")
    response = input("Is this the correct file? [Y/n]: ").strip().lower()

    if response in ("", "y", "yes"):
        input_file = DEFAULT_INPUT
    else:
        input_file = input("Please enter the input file path: ").strip()

    if not Path(input_file).exists():
        raise FileNotFoundError(f"File not found: {input_file}")

    extract_bibtex_entries(input_file, DEFAULT_OUTPUT)


if __name__ == "__main__":
    main()
