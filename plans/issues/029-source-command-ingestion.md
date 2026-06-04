# Issue 029 — Source Command Ingestion

## Type

AFK

## What to build

Add `clipper source INPUT --name SOURCE` as the source-ingestion command for remote URLs and local files. The command should download or copy exactly one media asset into `.clipper/sources/{source}/source.{ext}` and write flattened `metadata.json` beside it. Keep `clipper start` as a deprecated compatibility alias that performs the same source-ingestion behavior.

## Acceptance criteria

- [ ] `clipper source URL_OR_PATH --name source-name` creates `.clipper/sources/source-name/`.
- [ ] Remote inputs still use yt-dlp and support `--proxy`.
- [ ] Local inputs are copied into the source folder.
- [ ] Metadata is written to `.clipper/sources/{source}/metadata.json` and references the flattened source file path, e.g. `source.webm`.
- [ ] `--reuse` and `--force` follow the existing output policy semantics.
- [ ] `clipper start` still works as a deprecated alias for source ingestion.
- [ ] JSON and human output identify the source name and flattened artifact paths.

## Blocked by

- plans/issues/028-source-and-project-layouts.md
