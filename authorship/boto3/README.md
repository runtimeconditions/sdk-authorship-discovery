# Superseded combined-boto3 packaging rehearsal

## Status

**Historical checkpoint only. Do not use this directory as the current mapping contract or packaging workflow.**

This rehearsal proved that static Runtime Conditions metadata could be staged into a locally built boto3 wheel, installed without a registry, discovered without importing boto3, and exercised without changing application code. It also exposed a decisive ownership problem: the combined artifact assigned botocore operations and s3transfer behavior to the boto3 release even though those dependencies are versioned independently.

The owner-aligned implementation under [`../aws-python`](../aws-python/) supersedes this layout. Current service semantics, extension releases, mapping document kinds, generators, package staging, recursive discovery, and maintenance automation are documented there and under [`../../../extensions/aws-s3`](../../../extensions/aws-s3/).

The files retained in this directory are evidence of the earlier design checkpoint:

- [`results/2026-08-14-packaging-rehearsal.md`](results/2026-08-14-packaging-rehearsal.md) records what the local-wheel experiment proved and the limitations known at that point.
- [`patches`](patches/) contains the combined-artifact package-data experiment.
- [`tools`](tools/) contains the superseded candidate index, staging, and discovery implementation used for that rehearsal.
- [`fixture`](fixture/) contains the static candidate artifact used by the historical package proof.

Those artifacts intentionally retain their historical candidate names and extension identifier. They are not inputs to the current generators, validators, or workflows.
