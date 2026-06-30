# CBZ/CBR to KePub Converter - Web UI

Standalone batch converter with a browser UI, no Grimmory involved. No size
limits other than what your NAS's disk/CPU can handle.

Pipeline: CBZ/CBR -> EPUB (Calibre's `ebook-convert`) -> real KePub
(`kepubify`, the same tool Grimmory uses internally - genuine KePub output,
so you get the Kobo reading stats and faster page turns).

## Run (Synology / Container Manager / Portainer)

1. Copy this folder onto your NAS
2. Edit `docker-compose.yml`: point the two volume mounts at your actual CBZ
   folder and wherever you want converted files to land
3. Build and run:

   ```bash
   docker compose up -d --build
   ```

   (First build takes a few minutes - it's downloading and installing Calibre.)

4. Open `http://<nas-ip>:5010`

## Using it

1. Pick the folder to convert (or use the input root directly for a flat
   folder of files)
2. Set conversion options:
   - **Right-to-left** - manga page order (on by default)
   - **Grayscale** - smaller files, skips color art - leave off for colored manga
   - **Max image width/height** - optional, shrinks oversized pages
   - **Hyphenate** / **Smarten punctuation** - kepubify text options
   - **Skip existing** - safe to re-run on a partially-converted folder
3. Click **Start Conversion** - you'll land on a live progress page that
   polls every 2 seconds and shows per-file status (pending / converting /
   done / skipped / failed), so the browser never just hangs waiting

Failed files show their error inline in the table - usually either Calibre
or kepubify printing exactly what went wrong.

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
- The comic conversion flags (`--right2left`, `--colors`,
  `--comic-image-size`) come from Calibre's CLI conventions - if one errors
  on your installed Calibre version, the per-file error in the progress
  table will show exactly which flag and why, so it's easy to spot.
- This app only does conversion, not a persistent library - re-running on
  the same folder with "Skip existing" on just fills in anything new.
- If the container restarts mid-job, in-progress jobs are lost (job state
  lives in memory) - just re-run, "Skip existing" means already-converted
  files won't be redone.
