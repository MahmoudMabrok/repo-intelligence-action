# Example: how to use this action

Add a workflow to any repo:

```yaml
name: Repo Intelligence
on: [push, pull_request, workflow_dispatch]
jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: MahmoudMabrok/repo-intelligence-action@main
        with:
          fail_on_gates: "false"
```

Download the `repo-intelligence-report` artifact after the run, or read the job summary.
