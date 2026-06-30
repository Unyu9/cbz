# CBZ/CBR to KePub Converter

Standalone batch converter, no Grimmory involved. No size limits other than
what your NAS's disk/CPU can handle.

Pipeline: CBZ/CBR -> EPUB (Calibre's `ebook-convert`) -> real KePub (`kepubify`,
the same tool Grimmory uses internally - genuine KePub output, so you get the
Kobo reading stats and faster page turns).

## Build

```bash
docker build -t cbz-to-kepub .
```

(First build will take a few minutes - it's downloading and installing Calibre.)

## Run

```bash
docker run --rm \
  -v "/path/to/your/cbz/folder:/input" \
  -v "/path/to/output/folder:/output" \
  cbz-to-kepub
```

Every `.cbz`/`.cbr` in the input folder gets converted to a `.kepub.epub` in
the output folder. Already-converted files (matching output name already
present) are skipped, so it's safe to re-run on a folder you've partially
processed.

## Getting files onto your Kobo

Once converted, copy the `.kepub.epub` files onto your Kobo:

- **USB**: connect via cable, drag the files into the Kobo's storage
- **Calibre**: import the `.kepub.epub` files into a Calibre library and use
  "Send to device" with the Kobo connected

No further conversion happens at that point - `.kepub.epub` is a format the
Kobo already understands natively.

## Notes

- Large files (500MB+) will take a while and use real CPU/temp disk space
  during conversion - that's expected, this is the same workload Grimmory
  was doing, just without an arbitrary cap.
- If a file fails, check the log path printed at the end of the run (kept
  inside the container's temp dir while it's running - if you want logs to
  persist after a failure, mount a volume for `/tmp` too, or drop `--rm` and
  inspect the stopped container before removing it).
- `--output-profile kobo` tells Calibre to optimize the intermediate EPUB
  for Kobo's screen before kepubify does the real KePub conversion.
