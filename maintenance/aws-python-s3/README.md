# AWS Python historical maintenance experiment

This experiment measures whether owner-aligned SDK mappings can follow real boto3, botocore, and s3transfer releases without routine handwritten maintenance. S3 supplies the concrete mapping, but the measured subject is SDK authorship and maintenance.

## Evidence rule

The runner never edits or approves semantic overlays. It classifies a release as `automatic`, `review-required`, or `invalid`, generates deterministic artifacts, and records the exact SDK, extension, and experiment revisions used. A human records review time and disposition separately when a review is required.

Generated mappings, source checkouts, virtual environments, and wheels remain under ignored work or workflow-artifact directories. Accepted `run.json` and `report.md` files may be committed under `evidence/aws-python/` so the historical conclusions do not depend on GitHub Actions artifact retention.

## Local single-release run

Run the accepted baseline with locally available official source checkouts:

```sh
.venv/bin/python authorship/aws-python/tools/run_release_maintenance.py \
  --experiment maintenance/aws-python-s3/experiment.json \
  --release baseline-1.43.70 \
  --extensions-root ../extensions \
  --source boto3=.work/boto3-1.43.70 \
  --source botocore=.work/botocore-1.43.70 \
  --source s3transfer=.work/s3transfer-0.19.2-owner \
  --work-root .work/maintenance \
  --output .work/maintenance-evidence/baseline-1.43.70
```

Omit the `--source` arguments to fetch immutable upstream tags into the shared source cache. Use `--static-only` while developing generation and source classification; the default also patches package data, builds wheels, installs the owner graph, discovers mappings, validates runtime surfaces, and runs the application fixtures.

## Historical replay

[`../../.github/workflows/historical-releases.yml`](../../.github/workflows/historical-releases.yml) invokes [`../../authorship/aws-python/tools/replay_releases.py`](../../authorship/aws-python/tools/replay_releases.py) through a manual GitHub Actions dispatch. The workflow accepts an extension revision and an optional comma-separated release-id selection. With no selection, it runs every release tuple in `experiment.json`.

The manifest begins with ten consecutive boto3/botocore release tuples ending at the accepted baseline and uses the compatible s3transfer release selected for this sample. Add further historical tuples deliberately after confirming their immutable upstream tags and compatible package versions. Historical results must not be inferred from whatever dependency versions happen to be newest when a workflow runs.
