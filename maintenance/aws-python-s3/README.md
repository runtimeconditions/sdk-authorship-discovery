# AWS Python SDK maintenance experiment

This experiment measures whether owner-aligned SDK mappings can follow real boto3, botocore, and s3transfer releases without routine handwritten maintenance. S3 supplies the concrete mapping, but the measured subject is SDK authorship, ownership, and recurring maintenance.

## Two independent maintenance lanes

The AWS S3 extension repository observes AWS's authoritative public Smithy model. The SDK repository observes the language-specific package graph. The extension lane decides whether the accepted S3 vocabulary still represents the API; the SDK lane decides whether a particular boto3, botocore, and s3transfer graph still binds to that exact vocabulary.

The SDK lane verifies the immutable extension identifier, extension version, extension semantic digest, and service-mapping digest. One extension release may therefore support many SDK releases without a handwritten compatibility matrix, while a semantic extension release causes the latest SDK graph to be revalidated.

## Classifications

- `automatic` means the accepted extension semantics required no edit and every requested SDK gate passed.
- `extension-review-required` means the selected SDK release cannot align safely to the selected extension release.
- `sdk-review-required` means the extension remains sufficient but an SDK-owned public surface, wrapper, dependency, or package integration changed.
- `invalid` means the automation or input failed before semantic ownership could be classified safely.

The runner never edits or approves a semantic overlay. A human records disposition and review time when review is required. The mapping layer does not declare coverage percentages or unresolved application observations.

## Evidence policy

Generated mappings, source checkouts, temporary package trees, and wheels remain in ignored work directories or complete GitHub Actions artifacts. Concise `candidate.yaml`, `run.yaml`, and `report.md` records are committed under `evidence/aws-python/ongoing/` so conclusions do not depend on artifact retention. [`observations.yaml`](observations.yaml) is the durable cursor and records the exact SDK tuple and extension semantics already observed.

## Historical replay

[`../../.github/workflows/historical-releases.yml`](../../.github/workflows/historical-releases.yml) runs configured immutable tuples from [`experiment.yaml`](experiment.yaml) through a manual GitHub Actions dispatch. The initial sample contains ten consecutive boto3/botocore releases from 1.43.61 through 1.43.70 with s3transfer 0.19.2. Historical tuples are explicit so their meaning cannot change when a newer compatible dependency is published.

## Ongoing observation

[`../../.github/workflows/ongoing-releases.yml`](../../.github/workflows/ongoing-releases.yml) runs daily and can also be dispatched manually. It performs this sequence:

1. List stable tags from the three official upstream repositories.
2. Select the next unobserved boto3 release after the configured floor, preferring the same botocore release when boto3's declared range permits it; once the root backlog is exhausted, observe a changed latest-compatible dependency graph or changed extension semantic digest.
3. Read boto3's dependency requirements from the immutable tagged source and select a compatible botocore and s3transfer tuple.
4. Run extension-alignment, generation, source, recursive-reference, representative-resolution, packaging, installed-discovery, runtime-surface, dependency, and application-fixture gates.
5. Store complete temporary artifacts for 90 days and create a focused pull request containing durable evidence and the updated observation cursor; while that pull request remains open, scheduled runs recognize it and do not repeat the expensive proof.
6. Create or update a deduplicated issue when extension review, SDK review, or automation repair is required.

The observer is deliberately scoped to a boto3-rooted graph because that is the application and packaging surface proved by this experiment. A future owner-isolated lane is still needed to observe a botocore or s3transfer release that cannot participate in any valid boto3 graph.

## Local single-release run

Run a configured historical release with official local source checkouts:

```sh
python3 authorship/aws-python/tools/run_release_maintenance.py \
  --experiment maintenance/aws-python-s3/experiment.yaml \
  --release baseline-1.43.70 \
  --extensions-root ../extensions \
  --source boto3=/absolute/path/to/boto3-1.43.70 \
  --source botocore=/absolute/path/to/botocore-1.43.70 \
  --source s3transfer=/absolute/path/to/s3transfer-0.19.2 \
  --work-root .work/maintenance \
  --output .work/maintenance-evidence/baseline-1.43.70
```

Omit the `--source` arguments to fetch immutable upstream tags into the shared cache. Use `--static-only` while developing generation and source classification. The default also patches package data, builds wheels, installs the owner graph, discovers packaged mappings, validates runtime surfaces and dependency compatibility, and runs all application fixtures.

Resolve a live candidate independently with:

```sh
python3 authorship/aws-python/tools/resolve_release_candidate.py \
  --experiment maintenance/aws-python-s3/experiment.yaml \
  --state maintenance/aws-python-s3/observations.yaml \
  --extensions-root ../extensions \
  --source-cache .work/maintenance-source-cache \
  --output .work/release-candidate.yaml
```

Pass that output to the runner with `--release-file .work/release-candidate.yaml`.

## Current evidence

The ten-release historical sample was automatic. The first ongoing observation resolved boto3 1.43.79, botocore 1.43.79, and s3transfer 0.19.2 and passed the full proof without a semantic mapping change. That release establishes the ongoing observer's floor; future runs process every later boto3 release rather than attempting to turn the deliberate gap between the historical sample and live observation into another backfill. Its focused report is under [`../../evidence/aws-python/ongoing/ongoing-boto3-1.43.79-botocore-1.43.79-s3transfer-0.19.2`](../../evidence/aws-python/ongoing/ongoing-boto3-1.43.79-botocore-1.43.79-s3transfer-0.19.2/).
