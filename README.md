# Repo Intelligence GitHub Action

A transparent, auditable GitHub Action that collects the useful metrics from repository analysis tools:

- Source lines of code and file counts (via official [scc](https://github.com/boyter/scc) release)
- Git history: commits, contributors, development span
- README presence and length
- Optional secret scan (via official [gitleaks](https://github.com/gitleaks/gitleaks) binary)
- Simple acceptance gates
- JSON report uploaded as an artifact + job summary

No bundled binaries. No hidden network calls beyond the public GitHub release downloads for `scc` and `gitleaks`.

## Usage

Use the published action:

```yaml
name: Repo Intelligence

on:
  push:
  pull_request:
  workflow_dispatch:

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Analyze
        uses: MahmoudMabrok/repo-intelligence-action@main
        with:
          min_source_files: "20"
          min_loc: "5000"
          min_contributors: "2"
          min_commits: "100"
          min_months: "6"
          require_readme: "true"
          scan_secrets: "true"
          fail_on_gates: "false"
```

## Inputs

| Input | Default | Description |
|-------|---------|-------------|
| `min_source_files` | `20` | Minimum source files |
| `min_loc` | `5000` | Minimum source LOC |
| `min_contributors` | `2` | Minimum distinct authors |
| `min_commits` | `100` | Minimum commits |
| `min_months` | `6` | Minimum span in months |
| `require_readme` | `true` | Require README ≥ 200 chars |
| `scan_secrets` | `true` | Run gitleaks |
| `fail_on_gates` | `false` | Fail the job if gates miss |

## Outputs

- `report.json` artifact with full metrics
- Job summary in the Actions UI
- Step outputs: `passed`, `loc`, `report_path`

## Notes

- Full git history is fetched (`fetch-depth: 0`).
- Secret findings are counted only; the detailed gitleaks JSON is also written if the scan runs.
- Gate thresholds are adjustable. Defaults are illustrative.
- This does **not** clone other private repos or require extra tokens beyond the default `GITHUB_TOKEN` for checkout.

## License

Use freely. Built for transparency so you can audit every step.
