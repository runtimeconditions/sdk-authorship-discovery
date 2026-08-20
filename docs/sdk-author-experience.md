# SDK Author Experience

## Status

The owner-aligned AWS SDK for Python workflow is implemented and locally proved
for S3. It remains a candidate architecture until it is reviewed with actual
maintainers; no profiler contract has been accepted and no profiler was changed.

The exact files, validation commands, package patches, local-wheel workflow,
measurements, and maintenance rules are under
[`../authorship/aws-python`](../authorship/aws-python/). The earlier
[`../authorship/boto3`](../authorship/boto3/) rehearsal is retained as the
checkpoint that exposed the ownership flaw in a combined boto3 artifact.

## Current proposal

An SDK repository maintains only the semantic layer it owns and generates the
bulk metadata from models already used to produce the SDK. For the AWS Python
packages:

- botocore owns canonical service operations and generated client behavior;
- boto3 owns factories, its resource model, aliases, and handwritten wrappers;
- s3transfer owns managed-transfer entrypoints and classic/CRT execution paths.

Mappings compose through owner-qualified `operationRef`, `waiterRef`, and
`callRef` values. Each mapping version must equal its owning installed
distribution version. This avoids a Runtime Conditions compatibility lock:
ordinary dependency resolution continues to select package versions, and each
selected package supplies metadata for the behavior it versions.

## First integration burden

The proved first-time steps are within the previously accepted upper bound:

1. Adopt a small extension-aligned service semantic overlay.
2. Adopt a small handwritten-surface overlay where existing SDK models do not
   describe public wrappers.
3. Enable deterministic mapping generation in the existing model/codegen
   workflow.
4. Add two package-data patterns for the generated index and mappings.
5. Run static source/reference gates and retain representative resolution
   fixtures.
6. Ship generated metadata in the normal SDK artifact.

There is no Runtime Conditions runtime dependency, public SDK API change, or
generated-client rewrite. For the three Python packages the only build-source
change was adding the two package-data paths.

The authored S3 review surface is:

- one canonical service semantic overlay shared across languages;
- one boto3 wrapper/factory overlay;
- one s3transfer behavior overlay.

The maintainer does not review or edit 179,784 bytes of generated JSON. They review
the small semantic diff, upstream model/source change, operation/resource
counts, digests, validation diagnostics, and representative traces.

## Validation and maintenance experience

The source gate reads pinned SDK source without importing it and rejects:

- distribution-version mismatch;
- service operation or resource-model drift;
- stale generated Python names;
- changed positional/keyword wrapper bindings;
- missing or extra s3transfer service operations;
- changed public transfer entrypoints.

The recursive gate rejects missing mappings, undeclared dependencies, dangling
operation/waiter/call references, Condition-operation mismatches, and cycles.

This was not merely theoretical: the source gate found an off-by-one positional
binding in the initial `S3Transfer.download_file` metadata. The focused
annotation was corrected before packaging.

Routine generated operation and resource changes should require no per-language
hand edit. New semantic scope, a handwritten wrapper change, or a changed
transfer execution path requires a focused overlay review. A new generated
language consumes canonical service semantics and its SDK generator model; it
does not reimplement the S3 operation table.

## Application experience

The application developer installs and versions the SDK normally. The mapping
arrives inside packages already selected by the dependency resolver. They write
no mapping file, evidence file, compatibility lock, or annotation for a mapped
call and add no runtime dependency.

The local proof installed all three rebuilt wheels directly by file path, found
and digest-verified them without importing SDK modules, passed all six original
application tests unchanged, and passed the added managed-transfer fixture. The
compressed cost across all three wheels was
11,678 bytes.

When an SDK mapping is unavailable or application detection is incomplete, the
extension-provided no-op binding and project-local overrides remain the
application escape hatch. Application developers should not be expected to
author an SDK mapping.

The mapping layer does not declare coverage percentages or unresolved
observations. Developers, platform teams, profilers, CI policy, and downstream
adapters decide how to handle incomplete detection.

## Participation and ownership

Community and SDK-owner mappings are both valid adoption paths. SDK owners will
be solicited as first adopters, but participation is not assumed. A mapping
adopted and shipped by an SDK repository follows that repository's governance
and release lifecycle; an external community artifact follows its publisher's
governance and must identify its authority and target package versions.

The owner-aligned graph is about behavioral version authority, not company
ownership. Anyone may propose the metadata, but an artifact should not claim
that one distribution versions public behavior actually owned by another.

## Design red lines

- no significant SDK rewrite;
- no independently handwritten operation table per language;
- no recurring edit for ordinary generated releases;
- no Runtime Conditions runtime code in the application process;
- no request that maintainers review generated mapping JSON line by line;
- no SDK mapping that invents extension fields, credential conventions, or
  adapter policy;
- no false implication that every mutually exclusive transfer branch executes.

## Remaining maintainer interview questions

The implementation is now concrete enough for maintainer review. The interview
should test:

1. Is the three-overlay S3 review surface acceptable, and which existing AWS
   teams would own each overlay?
2. Would the package-data addition be accepted in the normal artifacts, or is a
   version-aligned additional artifact preferable?
3. Are the source-gate diagnostics sufficient for a failed release build?
4. Is the execution-path vocabulary faithful to how s3transfer maintainers
   reason about classic, CRT, multipart, cleanup, and conditional follow-up
   operations?
5. Which parts should be Smithy traits versus externally maintained overlays
   during first adoption?
6. What generated summary and fixtures would maintainers actually review on
   every operation-model change?

## Decision ledger

| Date | Decision | SDK-author impact |
| --- | --- | --- |
| 2026-08-13 | Treat existing SDK mapping conventions as disposable and optimize first for application adoption. | No prior manifest or profiler behavior constrains the design. |
| 2026-08-13 | Model AWS S3 with canonical operation objects aligned to the AWS extension. | SDK mappings preserve service calls; adapters own authorization translation. |
| 2026-08-13 | Generate the complete S3 service operation list from the canonical model. | Maintainers review semantic exceptions and drift, not 116 operations per language. |
| 2026-08-14 | Prove static mapping delivery in a local boto3 wheel. | Packaging needs no runtime dependency, but the combined mapping exposed a version-owner flaw. |
| 2026-08-14 | Split metadata across botocore, boto3, and s3transfer and compose it recursively. | Each package maintains only behavior it versions; nested wrappers do not force duplication. |
| 2026-08-14 | Validate handwritten bindings and implementation operation sets against pinned source. | Wrapper drift becomes a focused build error; the gate caught a real annotation defect. |
| 2026-08-14 | Preserve mutually exclusive runtime execution paths in transfer metadata. | SDK authors describe actual behavior without forcing mapping-layer policy for ambiguous application source. |
