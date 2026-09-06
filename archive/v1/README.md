# Personal site v1 archive

This directory preserves the tracked source of the personal site immediately
before the Soda Fountain redesign.

- Snapshot date: 2026-09-06
- Source revision: `origin/main`
- Source commit: `082075b8f0694afed998e5aa55d90d79dac8aec0`
- Files copied: 40
- Snapshot root: `archive/v1/site/`

## What is included

Every file tracked at the source commit, with repository-relative paths
preserved. This makes the version directly comparable with later site source and
keeps the templates, content, assets, configuration, and validation utilities
together.

## What is excluded

Untracked files, design prototypes, local caches, generated previews, and the
new portrait inputs were intentionally excluded. The design-reference stills
on the working branch postdate the v1 source commit and remain separately under
`_originals/design-reference/` at the repository root.

The root Jekyll configuration excludes `archive/`, so this snapshot remains a
repository reference rather than becoming a second published copy of the site.

## Compare or restore

Compare a current file with its v1 counterpart, for example:

```powershell
git diff --no-index archive/v1/site/index.html index.html
```

To inspect the exact original commit without using this directory:

```powershell
git show 082075b8f0694afed998e5aa55d90d79dac8aec0:index.html
```
