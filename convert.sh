#!/bin/bash
# Batch-converts every .cbz/.cbr in /input to a real .kepub.epub in /output.
#
# Pipeline: CBZ/CBR -> EPUB (Calibre's ebook-convert) -> KePub (kepubify)
#
# Usage (see docker run example in README.md):
#   docker run --rm -v /path/to/cbz/folder:/input -v /path/to/output:/output cbz-to-kepub

set -euo pipefail

INPUT_DIR="${INPUT_DIR:-/input}"
OUTPUT_DIR="${OUTPUT_DIR:-/output}"
TMP_DIR="$(mktemp -d)"

mkdir -p "$OUTPUT_DIR"

shopt -s nullglob nocaseglob
files=("$INPUT_DIR"/*.cbz "$INPUT_DIR"/*.cbr)
shopt -u nocaseglob

if [ ${#files[@]} -eq 0 ]; then
    echo "No .cbz/.cbr files found in $INPUT_DIR"
    exit 0
fi

total=${#files[@]}
count=0
failed=()

for src in "${files[@]}"; do
    count=$((count + 1))
    base="$(basename "$src")"
    name="${base%.*}"
    epub_path="$TMP_DIR/$name.epub"
    kepub_out="$OUTPUT_DIR/$name.kepub.epub"

    if [ -f "$kepub_out" ]; then
        echo "[$count/$total] Skipping (already exists): $name"
        continue
    fi

    echo "[$count/$total] Converting: $base"

    # ebook-convert occasionally wants a display available even for
    # non-interactive conversions - xvfb-run provides a virtual one.
    if xvfb-run -a ebook-convert "$src" "$epub_path" --output-profile kobo 2>"$TMP_DIR/$name.convert.log"; then
        if kepubify --inplace --update -o "$OUTPUT_DIR" "$epub_path" 2>"$TMP_DIR/$name.kepubify.log"; then
            # kepubify names output after the input file - rename to match source
            produced="$OUTPUT_DIR/$name.kepub.epub"
            if [ -f "$produced" ]; then
                echo "    -> $produced"
            else
                echo "    !! kepubify reported success but expected output not found: $produced"
                failed+=("$base")
            fi
        else
            echo "    !! kepubify failed - see $TMP_DIR/$name.kepubify.log"
            failed+=("$base")
        fi
    else
        echo "    !! ebook-convert failed - see $TMP_DIR/$name.convert.log"
        failed+=("$base")
    fi

    rm -f "$epub_path"
done

echo ""
echo "Done. $((total - ${#failed[@]}))/$total converted successfully."
if [ ${#failed[@]} -gt 0 ]; then
    echo "Failed:"
    printf '  - %s\n' "${failed[@]}"
    echo "Logs kept in: $TMP_DIR (container will be removed on exit if run with --rm)"
    exit 1
fi
