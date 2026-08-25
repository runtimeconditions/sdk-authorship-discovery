# AWS SDK for Python owner-aligned authorship proof

## Status

**Implemented and locally proved; not yet accepted profiler input.**

Start with [`REVIEW.md`](REVIEW.md) for the cohesive adoption, authorship, ownership, maintenance, and next-step argument. [`mapping-contract.md`](mapping-contract.md) records the exact mapping, dependency, discovery, and failure contract implemented here.

The proof packages the S3 mapping across the three Python distributions that own the public behavior:

| Distribution | Metadata it owns | What it references |
| --- | --- | --- |
| `botocore` 1.43.70 baseline | 116 low-level client methods resolving to 112 canonical S3 operations, eight paginators, four waiters, and extension-aligned Condition templates | the exact AWS S3 extension release |
| `s3transfer` 0.19.2 baseline | nine public transfer entrypoints, four logical transfer calls, and classic/CRT execution paths | botocore operations |
| `boto3` 1.43.70 baseline | client/resource factories, the complete S3 resource graph, resource waiters, and 17 managed-transfer wrapper surfaces | botocore operations, botocore waiters, and s3transfer calls |

All three wheels were built from official tagged source, installed by local file path, and discovered recursively without importing the SDK packages. Seven application projects passed unchanged. No profiler was modified.

The earlier combined-boto3 checkpoint under [`../boto3`](../boto3/) proved package delivery but associated independently versioned botocore and s3transfer behavior with the wrong owner. This implementation supersedes that layout.

## Why there are three mappings

The application depends directly on boto3, but boto3 accepts ranges of botocore and s3transfer versions. Embedding all behavior in a boto3-versioned artifact would make boto3 claim authority over independently released low-level operations and transfer behavior.

The mapping graph uses explicit owner-qualified references:

```text
boto3 Bucket.upload_file
  -> s3transfer managed-upload
    -> selected classic or CRT execution path
      -> botocore PutObject or multipart operations
        -> aws.s3 / bucket Conditions
```

Each installed distribution validates its own mapping against its exact version. Ordinary dependency declarations still resolve package compatibility; Runtime Conditions adds no application compatibility lock.

Recursion follows semantic behavior rather than every package in the runtime dependency tree. s3transfer selects S3 behavior before a serialized request reaches awscrt, so awscrt is transport rather than another Runtime Conditions semantic owner. urllib3, jmespath, dateutil, and similar support packages stop for the same reason. A lower package becomes another mapping node only when its owned public behavior introduces a meaningful resource step or another Runtime Condition.

## Extension relationship

AWS's public Smithy model and [`../../../extensions/aws-s3/model/runtimeconditions.smithy.yaml`](../../../extensions/aws-s3/model/runtimeconditions.smithy.yaml) generate the language-neutral S3 service mapping and immutable extension release. botocore then binds its versioned SDK surface to that canonical mapping.

The authoritative extension vocabulary contains 112 canonical operations. botocore 1.43.70 exposes 116 client methods because four deprecated SDK compatibility names remain; [`../../../extensions/aws-s3/model/botocore-sdk-annotations.yaml`](../../../extensions/aws-s3/model/botocore-sdk-annotations.yaml) maps them to their canonical operations. SDK aliases do not expand extension vocabulary.

The terminal botocore mapping records the exact extension identifier, extension version, extension semantic digest, and service-mapping digest. Higher-level mappings reach that contract through required owner-qualified dependencies, and recursive validation rejects a graph whose terminal semantics differ. Many SDK releases can target one immutable extension release, and an extension semantic change causes the latest SDK graph to be revalidated.

## Maintainer-authored inputs

Maintainers review compact semantic inputs, not generated YAML:

- [`../../../extensions/aws-s3/model/runtimeconditions.smithy.yaml`](../../../extensions/aws-s3/model/runtimeconditions.smithy.yaml) classifies authoritative S3 operations, resource identity paths, roles, and secondary resources once for all languages.
- [`../../../extensions/aws-s3/model/botocore-sdk-annotations.yaml`](../../../extensions/aws-s3/model/botocore-sdk-annotations.yaml) records botocore-only compatibility operation aliases.
- [`../../../extensions/aws-s3/model/boto3-wrapper-annotations.yaml`](../../../extensions/aws-s3/model/boto3-wrapper-annotations.yaml) identifies boto3 aliases, factories, handwritten wrappers, and two handwritten resource loads; its existing resource model supplies the rest of the resource graph.
- [`../../../extensions/aws-s3/model/s3transfer-semantic-annotations.yaml`](../../../extensions/aws-s3/model/s3transfer-semantic-annotations.yaml) describes transfer entrypoints and classic or CRT execution paths.

Generated mappings are stored under [`../../../extensions/aws-s3/mappings`](../../../extensions/aws-s3/mappings/). `operationRef`, `waiterRef`, and `callRef` values are owner-qualified and cannot resolve by an accidental matching name.

Execution paths and predicates describe SDK behavior. They are not coverage percentages or unresolved observations. A profiler or downstream policy decides what to do when source cannot prove which runtime path will be selected.

## Source and graph validation

The source gate reads SDK files as data and does not import an SDK. It rejects an owner-version mismatch, missing or extra SDK operation, stale generated spelling, invalid compatibility alias, stale positional or keyword binding, resource inventory drift, changed transfer signature, or transfer operation-set drift.

The cross-artifact gate rejects undeclared dependencies, dangling owner-qualified references, missing target members, noncanonical operations, Condition inconsistencies, extension identity or digest mismatches, and cycles.

During the initial rehearsal, source validation caught an incorrect `download_file` positional binding. Correcting the compact annotation made the gate pass, demonstrating that an actual maintenance defect produces a focused diagnostic.

## Package integration

Each repository adds two static package-data patterns and stages an index plus one mapping:

```text
<python-package>/
  runtimeconditions/
    index.yaml
    mappings/
      aws-s3.yaml
```

The exact package-data changes are under [`patches`](patches/). There is no Runtime Conditions import, runtime API, or runtime dependency.

The authoring and maintenance scripts use the dependencies in [`requirements.txt`](requirements.txt), including PyYAML for the first-party artifact contract. Those are generator dependencies only and are not added to boto3, botocore, s3transfer, or an application.

The reusable staging tool verifies the mapping owner and source version before copying static metadata:

```sh
python3 sdk/authorship/aws-python/tools/stage_distribution.py \
  --source-root /absolute/path/to/botocore-1.43.70 \
  --distribution botocore \
  --version-file botocore/__init__.py \
  --index-path botocore/runtimeconditions/index.yaml \
  --mapping extensions/aws-s3/mappings/botocore/runtimeconditions.sdk-mapping.yaml=botocore/runtimeconditions/mappings/aws-s3.yaml
```

Build through each repository's normal release process and install the resulting artifacts directly for a registry-free proof:

```sh
python -m pip install --no-deps --force-reinstall \
  /absolute/path/to/botocore-1.43.70-py3-none-any.whl \
  /absolute/path/to/s3transfer-0.19.2-py3-none-any.whl \
  /absolute/path/to/boto3-1.43.70-py3-none-any.whl
```

Discovery reads installed package metadata and YAML without importing SDK modules:

```sh
python3 sdk/authorship/aws-python/tools/discover_mappings.py \
  --root-distribution boto3 \
  --root-mapping boto3.aws.s3
```

## Measured packaging result

The YAML baseline mappings added 10,238 compressed bytes across the three wheels:

| Wheel | Baseline | With mapping | Increase |
| --- | ---: | ---: | ---: |
| boto3 | 140,125 B | 143,966 B | 3,841 B |
| botocore | 15,594,015 B | 15,598,390 B | 4,375 B |
| s3transfer | 90,317 B | 92,339 B | 2,022 B |

Installed discovery resolved botocore, then s3transfer, then boto3 without importing their modules. Dependency verification, runtime-surface checks, and all direct-client, session-client, resource, application-wrapper, dependency-injection, dynamic-service, and managed-transfer tests passed.

## Maintenance experiment

[`../../maintenance/aws-python-s3`](../../maintenance/aws-python-s3/) contains the historical and ongoing experiment. The single-release runner accepts configured historical tuples or a dynamically resolved release file, regenerates the complete owner graph, and returns one of four classifications: `automatic`, `extension-review-required`, `sdk-review-required`, or `invalid`.

The ten-release historical sample from boto3/botocore 1.43.61 through 1.43.70 was automatic. The first ongoing observation resolved boto3 1.43.79, botocore 1.43.79, and s3transfer 0.19.2 from official tags and boto3's source declarations. It passed all generation, package, installed-graph, runtime, and application gates with no semantic mapping change.

The daily observer processes unobserved boto3-rooted package graphs and revalidates the latest graph when the accepted extension semantic digest changes. It creates durable evidence and focused review routing. It does not yet cover owner-isolated releases that cannot participate in a valid boto3 graph.

## Application experience

For recognized calls, application developers install and version the SDK normally, write ordinary SDK code, and run the profiler locally or in CI. They do not add a mapping dependency, mapping file, evidence file, compatibility lock, or Runtime Conditions annotation.

When mapping support or static detection is incomplete, extension-provided no-op bindings and project-local overrides remain the intended escape hatches. Application developers should not become SDK mapping authors.

## Deliberately not done

- No profiler consumes these mappings yet; expanding a language profiler requires a separate discussion.
- No mapping claims fixed AWS credential or environment-variable conventions.
- No mapping declares coverage, unresolved observations, CI policy, or adapter failure behavior.
- No official or community artifact publication mechanism has been selected.
- No maintainer interview has yet tested whether the focused review burden is acceptable.
- The external Smithy compiler currently proves S3; an AWS-grade JVM plugin, all-services inventory, and additional language generators remain in the tracked all-services work.
