# Question bank provenance

The JSON in this directory is a **verbatim snapshot** — not authored here.

| | |
|---|---|
| Upstream | `connectry-architect-mcp` |
| Version | **0.1.13** |
| Repository | https://github.com/Connectry-io/connectry-architect-mcp |
| Licence | MIT — © 2026 Connectry LABS |
| Contents | 390 questions across 5 domains / 30 task statements, plus `curriculum.json` |

## Where it came from

`--sync` copies from the first source it finds:

1. `tools/connectrylab-architect-cert-mcp/src/data/` — the in-repo checkout of the
   MCP server (this is what the current snapshot was taken from)
2. `/opt/homebrew/lib/node_modules/connectry-architect-mcp/dist/data/` — the global
   npm install used by the `connectry-architect` MCP server

Both were verified byte-identical at v0.1.13. Override with `OFFLINE_ASSESSMENT_SOURCE`.

## Why snapshot instead of reading the source directly

- The in-repo copy sits inside its **own nested git checkout**, so a `pull` or `reset`
  there can move the data underneath the tool.
- The global npm copy moves or disappears on upgrade/uninstall.
- Pinning the bank keeps `history.jsonl` progression comparable across sessions — a
  changed question set would silently invalidate the trend.

Because this repo is not under version control, a clobbered `data/` has no recovery
path other than re-running `--sync`. `manifest.json` records a sha256 per file, and
`--selftest` verifies them, so silent corruption is detectable.

## Do not hand-edit

`--sync` overwrites every file here and rewrites `manifest.json`. Fixes belong upstream.
