# AWS SDK for Python owner-aligned authorship proof

## Status

**Implemented and locally proved; candidate contract, not yet accepted profiler input.**

For a cohesive explanation of the SDK authorship, adoption, ownership, and maintenance proposal before reviewing the individual artifacts, start with [`REVIEW.md`](REVIEW.md).

This proof packages the S3 mapping across the three Python distributions that
own the public behavior:

| Distribution | Metadata it owns | What it references |
| --- | --- | --- |
| `botocore` 1.43.70 | 116 low-level S3 operations, eight paginators, four waiters, and extension-aligned Condition templates | the AWS S3 extension |
| `s3transfer` 0.19.2 | nine public transfer entrypoints, four logical transfer calls, and their classic/CRT execution paths | botocore operations |
| `boto3` 1.43.70 | client/resource factories, its complete S3 resource graph, resource waiters, and 17 managed-transfer wrapper surfaces | botocore operations, botocore waiters, and s3transfer calls |

All three wheels were built from their official tagged source, installed by
local file path, and discovered recursively without importing `boto3`,
`botocore`, or `s3transfer`. All seven application projects passed
unchanged. No profiler was modified.

The proof uses s3transfer 0.19.2—the version the unchanged corpus environment
actually resolves for boto3's compatible range—rather than quietly forcing the
0.19.0 minimum. This is exactly why s3transfer owns and versions its mapping.

The earlier combined-boto3 checkpoint remains under
[`../boto3`](../boto3/). It proved package delivery but not correct version
ownership; this directory supersedes its mapping layout.

## Why there are three mappings

The application depends directly on boto3, but boto3 intentionally accepts a
range of botocore and s3transfer versions. Embedding all behavior in the boto3
artifact would associate botocore operations and transfer behavior with the
wrong release authority.

The candidate uses explicit references instead:

```text
boto3 Bucket.upload_file
  -> s3transfer managed-upload
    -> selected classic or CRT execution path
      -> botocore PutObject or multipart operations
        -> aws.s3 / bucket Conditions
```

Each installed distribution therefore validates its own mapping against its
exact installed version. This uses ordinary dependency versioning; it does not
add an application compatibility lock.

### Where recursion stops

The graph follows semantic SDK behavior, not every package in the runtime
dependency tree. The optional CRT path does not add an `awscrt` mapping:
s3transfer has already selected the S3 `PutObject`, `GetObject`, or
`DeleteObject` behavior before handing a serialized request to awscrt. awscrt is
the transport implementation and does not add a distinct external-resource
demand. The same is true of urllib3, jmespath, dateutil, and similar supporting
packages.

If a lower package exposed another public service contract or introduced a
separate Runtime Condition, it would become another owner mapping dependency.
Recursion therefore stops at the owner-qualified botocore operation that aligns
to the S3 extension, rather than stopping at an arbitrary package depth or
continuing into generic transport internals.

The implemented field semantics and required consumer failures are recorded in
[`mapping-contract.md`](mapping-contract.md).

## Maintainer-authored input

Maintainers review three compact semantic inputs, not the generated JSON:

- [`../../../extensions/aws-s3/model/semantic-annotations.json`](../../../extensions/aws-s3/model/semantic-annotations.json)
  defines the extension meaning of S3 service operations.
- [`../../../extensions/aws-s3/model/boto3-wrapper-annotations.json`](../../../extensions/aws-s3/model/boto3-wrapper-annotations.json)
  identifies boto3's aliases, factories, handwritten wrappers, and two
  handwritten resource loads. The rest of the resource graph comes from
  boto3's existing `resources-1.json` model.
- [`../../../extensions/aws-s3/model/s3transfer-semantic-annotations.json`](../../../extensions/aws-s3/model/s3transfer-semantic-annotations.json)
  defines the public transfer entrypoints and the operations used by each
  classic or CRT execution path.

Generated mappings are:

- [`botocore`](../../../extensions/aws-s3/mappings/botocore/runtimeconditions.sdk-mapping.json)
- [`s3transfer`](../../../extensions/aws-s3/mappings/s3transfer/runtimeconditions.sdk-mapping.json)
- [`boto3`](../../../extensions/aws-s3/mappings/boto3/runtimeconditions.sdk-mapping.json)

`operationRef`, `waiterRef`, and `callRef` are owner-qualified. A reference
cannot resolve merely because another mapping happens to use the same name; the
target distribution and mapping identity must also match.

Execution-path and predicate fields describe SDK behavior. They are not
coverage percentages or unresolved observations. A profiler or downstream
policy decides what to do when application source cannot prove which runtime
path will be selected.

## Source validation gate

The required source gate reads SDK files as data and does not import any SDK:

```sh
python3 extensions/aws-s3/tools/validate_sdk_sources.py \
  --boto3-source /absolute/path/to/boto3-1.43.70 \
  --botocore-source /absolute/path/to/botocore-1.43.70 \
  --s3transfer-source /absolute/path/to/s3transfer-0.19.2 \
  --boto3-annotations extensions/aws-s3/model/boto3-wrapper-annotations.json \
  --s3transfer-annotations extensions/aws-s3/model/s3transfer-semantic-annotations.json \
  --botocore-mapping extensions/aws-s3/mappings/botocore/runtimeconditions.sdk-mapping.json \
  --boto3-mapping extensions/aws-s3/mappings/boto3/runtimeconditions.sdk-mapping.json \
  --s3transfer-mapping extensions/aws-s3/mappings/s3transfer/runtimeconditions.sdk-mapping.json
```

It rejects:

- a mapping version that differs from the owning source package;
- any missing or extra botocore S3 operation;
- stale Python operation spellings;
- stale positional or keyword bindings for factories and handwritten wrappers;
- a boto3 resource inventory that differs from its resource model;
- an s3transfer public entrypoint whose signature changed;
- an s3transfer operation set that differs from the implementation modules.

During this rehearsal it rejected an incorrect `download_file` positional
binding. Correcting the annotation made the gate pass. This is an important
proof that maintenance failures produce reviewable diagnostics instead of
silently stale metadata.

The cross-artifact gate is:

```sh
python3 extensions/aws-s3/tools/validate_owner_mappings.py \
  --mapping extensions/aws-s3/mappings/botocore/runtimeconditions.sdk-mapping.json \
  --mapping extensions/aws-s3/mappings/s3transfer/runtimeconditions.sdk-mapping.json \
  --mapping extensions/aws-s3/mappings/boto3/runtimeconditions.sdk-mapping.json \
  --root-distribution boto3 \
  --root-mapping boto3.aws.s3
```

It checks declared dependencies, all recursive references, target members,
operation/Condition consistency, and dependency cycles.

## Package integration

Each repository adds two package-data patterns and stages an index plus one
mapping:

```text
<python-package>/
  runtimeconditions/
    index.json
    mappings/
      aws-s3.json
```

The exact build changes are:

- [`patches/botocore-package-data.patch`](patches/botocore-package-data.patch)
- [`patches/s3transfer-package-data.patch`](patches/s3transfer-package-data.patch)
- [`patches/boto3-package-data.patch`](patches/boto3-package-data.patch)

There is no Runtime Conditions import, runtime API, or runtime dependency. The
index records the owning distribution and exact version, mapping identity,
path, service, and SHA-256 digest.

Stage each mapping with the same reusable tool:

```sh
python3 sdk/authorship/aws-python/tools/stage_distribution.py \
  --source-root /absolute/path/to/botocore-1.43.70 \
  --distribution botocore \
  --version-file botocore/__init__.py \
  --index-path botocore/runtimeconditions/index.json \
  --mapping extensions/aws-s3/mappings/botocore/runtimeconditions.sdk-mapping.json=botocore/runtimeconditions/mappings/aws-s3.json
```

Use the corresponding package name and mapping for boto3 and s3transfer. The
tool stops if the mapping distribution or version does not match the source
tree and prints only mapping identities and digests for review.

Build with each repository's supported release command. The rehearsal used the
existing wheel build:

```sh
python3 setup.py bdist_wheel --dist-dir /absolute/path/to/wheelhouse
```

Install the three wheels directly; no registry is involved:

```sh
python -m pip install --no-deps --force-reinstall \
  /absolute/path/to/wheelhouse/botocore-1.43.70-py3-none-any.whl \
  /absolute/path/to/wheelhouse/s3transfer-0.19.2-py3-none-any.whl \
  /absolute/path/to/wheelhouse/boto3-1.43.70-py3-none-any.whl
```

Discover and validate the installed graph without SDK imports:

```sh
python sdk/authorship/aws-python/tools/discover_mappings.py \
  --root-distribution boto3 \
  --root-mapping boto3.aws.s3
```

## Measured result

The three uncompressed mapping files total 179,784 bytes. Compression limited
the wheel increases to 11,678 bytes total:

| Wheel | Baseline | With mapping | Increase |
| --- | ---: | ---: | ---: |
| boto3 | 140,125 B | 145,307 B | 5,182 B |
| botocore | 15,594,015 B | 15,598,079 B | 4,064 B |
| s3transfer | 90,317 B | 92,749 B | 2,432 B |

Installed discovery reported this dependency order:

```text
botocore: botocore.aws.s3
s3transfer: s3transfer.aws.s3
boto3: boto3.aws.s3
```

It also reported `false` for all three SDK-module import checks. `pip check`
reported no broken requirements, and all direct-client, session-client,
resource, application-wrapper, dependency-injection, dynamic-service, and
managed-transfer tests passed.

A separate post-install runtime surface test checked 116 generated client
methods, eight paginators, four waiters, 19 resource classes, and 148 resource
members. Six s3transfer entrypoints were checked at runtime; three CRT
entrypoints were source-validated but skipped at runtime because the optional
`awscrt` extra was deliberately not installed.

Representative recursive resolutions can be checked with
[`tools/resolve_s3_examples.py`](tools/resolve_s3_examples.py). It proves direct
`PutObject`, `Bucket.put_object`, `Bucket.wait_until_exists`, and
`Bucket.upload_file` chains down to extension Conditions.

## Routine maintenance burden

- A routine regenerated botocore operation requires no per-language edit. An
  operation-set change stops at the service fingerprint review gate.
- A boto3 resource-model change regenerates mechanically. A handwritten wrapper
  change requires one small binding or call-reference update.
- An s3transfer execution change requires updating the affected logical call's
  paths; source validation rejects a stale operation set or signature.
- A new AWS service reuses the index, packaging, discovery, reference, and
  validation machinery. It supplies service semantics and any handwritten
  wrapper overlays specific to that service.

The application developer still writes no mapping metadata and adds no
dependency. Missing detection remains addressable with extension-provided no-op
bindings and project-local overrides; it does not become application-authored
SDK mapping work.

## Deliberately not done

- No profiler consumes this candidate yet; that expansion still requires a
  separate discussion.
- No mapping claims a fixed AWS credential or environment-variable convention.
- No mapping declares coverage, unresolved observations, CI policy, or adapter
  failure behavior.
- This proof does not claim all AWS services are generated. The postponed
  all-services Smithy workflow remains documented under `todos/`.
