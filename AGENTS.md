# epg-mirror

This repository is an **EPG (Electronic Program Guide) mirror**. It has no application
code and no package manager. Its only job is a scheduled GitHub Actions workflow that
downloads a large XMLTV guide from an upstream source, gzip-compresses it, and commits
the result back to the repo.

- `.github/workflows/sync-epg.yml` — the only "code". Runs every 4 hours (and on manual
  dispatch). Downloads `http://epg.team/tvteam.xml.3.3` (fallback `http://epg.team/tvteam.3.3.xml`),
  runs `gzip -9`, and commits `tvteam.xml.gz` to `main`.
- `tvteam.xml.gz` — the committed data artifact (~40 MB compressed, ~280 MB XMLTV;
  ~3.7k channels, ~550k programmes).

## Cursor Cloud specific instructions

- There is nothing to build, no dependencies to install, and no dev server. The only
  tooling required is `curl`, `gzip`, and `git`, which are already present on the VM. The
  environment update script is intentionally a no-op.
- To run the pipeline end-to-end locally (the equivalent of the "app"), reproduce the
  workflow steps from `.github/workflows/sync-epg.yml`. Do this in a scratch dir like
  `/tmp`, NOT the repo root, unless you actually intend to update the committed artifact:
  ```
  cd /tmp
  UA="Mozilla/5.0"
  curl -L --fail -A "$UA" -o tvteam.xml "http://epg.team/tvteam.xml.3.3" \
    || curl -L --fail -A "$UA" -o tvteam.xml "http://epg.team/tvteam.3.3.xml"
  gzip -9 -c tvteam.xml > tvteam.xml.gz
  gzip -t tvteam.xml.gz   # integrity check
  ```
- "Lint/test": there is no lint or test suite. The meaningful validation is
  `gzip -t tvteam.xml.gz` (integrity) plus checking the decompressed head starts with
  `<?xml` / `<tv>` and contains `<channel>`/`<programme>` elements.
- Gotcha: two gz files produced from identical XML will still differ in their first few
  bytes because gzip embeds a modification timestamp in its header. Compare *content*
  (e.g. decompress and diff, or compare `gzip -l` sizes), not raw gz bytes.
- The download is large (~270 MB) and depends on the external host `epg.team` being
  reachable; egress to that host must be allowed for the pipeline to run.
