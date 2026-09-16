# Planned SDK Mapping Authorship and Registry Workflow

## Why This Document Exists

This document defines the actionable plan for creating, validating, publishing, and maintaining SDK mappings. It exists because the earlier research workflow accumulated service projections, semantic bridges, overlays, recursive owner graphs, maintenance reports, and generated files without producing an understandable SDK-author task.

This is the implementation plan for the replacement. It will be used to:

1. define the first compact SDK mapping format;
2. implement the boto3/S3 mapping and its validation tooling;
3. define the central open source registry layout and publication checks;
4. evaluate whether an SDK author can adopt and maintain the mapping without learning Runtime Conditions research internals; and
5. decide whether the same small contract is sufficient for another SDK before adding more mapping features.

It is not an additional research narrative. When implementation reveals that this plan is wrong, this document must be updated directly rather than supplemented with another design document.

The end-user resolution and generation experience is defined separately in [`planned-mapping-user-experience.md`](planned-mapping-user-experience.md). This document begins where that workflow obtains an already-authored mapping.

## Required Outcome

An SDK mapping connects a public SDK source pattern directly to vocabulary from an existing Runtime Conditions extension:

```text
public SDK construction and call pattern
  -> extension-defined Condition writes
```

For the first acceptance case:

```text
boto3.client("s3").put_object(Bucket=...)
  -> aws.s3 / bucket / PutObject

boto3.client("s3").upload_file(..., Bucket, ...)
  -> aws.s3 / bucket /
     PutObject + CreateMultipartUpload + UploadPart +
     CompleteMultipartUpload + AbortMultipartUpload
```

The `upload_file` mapping declares the conservative set of canonical S3 operations directly. It does not encode s3transfer implementation branches, predicates, recursive calls, or package-ownership graphs.

## Non-Negotiable Boundaries

The new workflow has none of the following required artifacts:

- authoritative service projection;
- Service Operations Inventory;
- Service Operations Semantic Bridge;
- language-neutral service mapping;
- SDK surface projection;
- semantic overlay;
- public-surface classification file;
- recursive SDK-owner graph;
- execution-path model;
- per-release maintenance report; or
- generated mapping YAML that a maintainer must review line by line.

An extension author may use Smithy, OpenAPI, protobuf, source generation, or any other private implementation technique to create an extension. An SDK author may use an SDK model or generator to create mapping rules. Those are optional authoring conveniences, not parts of the SDK mapping contract.

The mapping contract does not require complete SDK coverage. A mapping may support a useful subset of public calls. Unmapped packages and unsupported call patterns remain silent.

## Ownership

| Owner | Maintains |
| --- | --- |
| Extension author | Condition vocabulary, schemas, immutable extension releases, and generated extension bindings |
| SDK mapping author | The compact table connecting public SDK patterns directly to extension writes |
| SDK maintainer, when participating | Approval of mappings shipped with the SDK and validation in the SDK release workflow |
| Central registry maintainers | Mapping review, immutable publication, exact SDK-version validation records, catalog generation, and signing |
| Profiler maintainers | Generic language analysis and evaluation of the mapping contract |
| Application developer | Nothing for supported calls; an explicit local mapping or extension-binding declaration only when desired |

An SDK-owned mapping and a community-owned mapping use the same format. Authority affects review and precedence, not Condition semantics.

## One Maintained Mapping Artifact

The primary human-authored artifact is one YAML mapping for one SDK package and one extension. It contains:

- mapping identity and independent mapping release version;
- package ecosystem, package name, and language;
- one exact extension identifier;
- public SDK match rules;
- minimal produced receiver or resource identities needed by later rules;
- direct generic `writes[]` instructions; and
- optional Condition identity extraction.

It does not contain a copy of the extension, service operation templates, SDK source inventories, coverage claims, maintenance history, or generated evidence.

The initial shape is:

```yaml
apiVersion: runtimeconditions.io/sdk-mapping/v1alpha1
kind: RuntimeConditionsSDKMapping

metadata:
  name: boto3.aws-s3
  version: 0.1.0

sdk:
  ecosystem: pypi
  package: boto3
  language: python

extension:
  id: https://runtimeconditions.io/extensions/aws-s3/0.2.0/runtimeconditions.extension.yaml

rules: []
```

`metadata.version` versions the mapping rules independently from the SDK and extension. Published mapping releases are immutable. The central registry associates a successfully validated mapping release with exact SDK package versions; the mapping does not select or constrain the application's dependency version.

The example uses a future additive S3 extension release because `bucketName` is not defined by the immutable `0.1.0` release. The final identifier will be selected when that extension change is implemented.

## Minimum Rule Vocabulary

The first implementation supports only the constructs required by the agreed S3 slice:

1. Match a public function, constructor, or method symbol.
2. Match a literal selector argument, such as `service_name == "s3"`.
3. Record that a matched call produces a named SDK surface.
4. Match a later method call on that produced surface.
5. Read an argument by language parameter name with positional fallback where the SDK permits it.
6. Carry one resource identity from a producer to a later receiver method.
7. Write a constant or statically resolved argument value to an extension-defined Condition path.
8. Append one or more constant objects to an extension-defined array.

The first implementation does not include arbitrary predicates, general data-flow programming, delegated call graphs, implementation branches, callbacks, or a universal SDK state language.

New rule constructs may be added only when a concrete accepted SDK call cannot be expressed by this set. The plan and schema must be revised together; no SDK-specific hidden behavior may be added to a profiler.

## Direct boto3/S3 Mapping Shape

The exact schema will be fixed by implementation tests, but the intended authored content is equivalent to the following.

### Client construction

```yaml
- id: boto3-s3-client
  match:
    call:
      symbols:
        - boto3.client
        - boto3.Session.client
        - boto3.session.Session.client
      arguments:
        service:
          position: 0
          keyword: service_name
          equals: s3
  produces:
    surface: aws-s3-client
```

Client construction alone emits no Condition. It only proves the receiver type for later mapped calls.

### Direct `PutObject`

```yaml
- id: s3-put-object
  match:
    method:
      receiverSurface: aws-s3-client
      name: put_object
  condition:
    identity:
      argument:
        keyword: Bucket
    writes:
      - target: kind
        value: aws.s3
      - target: interface.type
        value: bucket
      - target: interface.bucketName
        argument:
          keyword: Bucket
        whenStaticallyKnown: true
      - target: interface.operations[]
        value:
          name: PutObject
```

`interface.bucketName` is optional. The argument contributes to static Condition identity even when its concrete value cannot be emitted. Calls proven to use two distinct bucket identities produce two Conditions. Calls proven to use the same identity may aggregate their operations.

### Managed upload

```yaml
- id: s3-upload-file
  match:
    method:
      receiverSurface: aws-s3-client
      name: upload_file
  condition:
    identity:
      argument:
        position: 1
        keyword: Bucket
    writes:
      - target: kind
        value: aws.s3
      - target: interface.type
        value: bucket
      - target: interface.bucketName
        argument:
          position: 1
          keyword: Bucket
        whenStaticallyKnown: true
      - target: interface.operations[]
        values:
          - name: PutObject
          - name: CreateMultipartUpload
          - name: UploadPart
          - name: CompleteMultipartUpload
          - name: AbortMultipartUpload
```

These operation names are canonical S3 vocabulary. The mapping does not expose a Runtime Conditions-defined `upload` capability and does not describe why boto3 may invoke each operation.

### Resource API

The first mapping also supports:

```text
boto3.resource("s3").Bucket(bucket).put_object(...)
```

This requires one producer rule for the S3 resource, one producer rule for `Bucket(bucket)` that retains the bucket identity, and one `put_object` receiver rule that writes `PutObject`. It must use the same eight primitive constructs and must not introduce a boto3 resource-model artifact.

## Relationship to Extension Bindings

SDK mappings and generated extension bindings use the same normalized `writes[]` instruction model:

- an extension binding call is an explicit declaration written by the application developer;
- an SDK mapping rule recognizes an ordinary third-party SDK call; and
- both produce a Condition by writing only fields and values defined by the selected extension.

The generic write evaluator is shared. SDK mappings do not define Condition vocabulary and cannot add fields or values missing from the extension.

## SDK Mapping Author Workflow

An SDK mapping author performs these steps:

1. Select one existing immutable extension release that expresses the required Condition.
2. Identify a small set of public SDK calls worth supporting.
3. Add one direct rule for each distinct source pattern.
4. Bind Condition identity only when the SDK call or receiver provides evidence for it.
5. Express output exclusively through generic `writes[]` instructions.
6. Add focused positive and negative source fixtures.
7. Validate the mapping against an exact released SDK package.
8. Publish it with the SDK, a companion package, or the central registry.

The author does not classify every public symbol, reproduce the SDK's operation inventory, model internal package ownership, or explain unmapped calls.

For model-generated SDKs, an SDK project may emit this same compact mapping from its existing generator. Generated authorship is optional; the published artifact and validation requirements are identical.

## Required Validation

A mapping release cannot be published until automation verifies:

1. The mapping document satisfies the SDK mapping schema.
2. The exact extension identifier resolves to an immutable extension definition.
3. Every `writes[].target` exists in the extension or core Condition model.
4. Every constant field value is permitted by the extension.
5. Every generated Condition used by a positive fixture passes extension validation.
6. Required SDK symbols, receiver methods, and named parameters exist in the exact SDK release under test.
7. Positive fixtures emit the expected Conditions.
8. Negative fixtures emit no Condition.
9. Two statically distinct S3 bucket identities produce two Conditions.
10. A statically known bucket name is emitted and an unknown bucket name remains omitted.

Validation may use the SDK's normal compiler, type information, generated model, package metadata, or isolated authoring-time introspection. That mechanism is tooling for validating the public contract; it is not serialized into the mapping and is never run during application profile generation.

The boto3 validator may inspect botocore's packaged S3 service model to verify dynamically generated methods. This is a validator implementation detail, not a second mapping layer or an obligation placed on application developers.

## Publication Paths

### SDK-bundled

An SDK repository keeps the mapping source beside its normal source or generator inputs, validates it in release CI, and publishes it at the ecosystem's deterministic Runtime Conditions package location. The package version itself supplies exact SDK-version alignment.

### Companion package

A companion package contains the same mapping artifact and declares its SDK compatibility through the ordinary package manager. It does not introduce a different mapping format or registry contract.

### Central open source registry

A community or SDK author submits the same mapping to the central registry. The registry validates it against exact SDK releases and publishes immutable mapping releases plus a generated ecosystem catalog.

An SDK-bundled mapping remains preferred over companion and registry mappings. Registry ownership never implies that the SDK vendor endorsed a community mapping.

## Central Registry Layout

The open source registry has one maintained mapping source per package-and-extension integration and focused executable fixtures. It does not require a README, design document, maintenance report, service mapping, or evidence file for every integration.

The intended source layout is:

```text
mappings/
  <ecosystem>/
    <package>/
      <mapping-name>/
        runtimeconditions.sdk-mapping.yaml
        tests/
          <focused source fixtures>
          <expected profiles>
```

Generated catalogs, content digests, validation attestations, and publication bundles are build outputs. They are not manually authored review surfaces.

Published releases are immutable and content-addressed or signed. The registry catalog is indexed by:

- package ecosystem;
- package name;
- exact SDK package version;
- mapping name and mapping release version; and
- mapping content digest.

The catalog contains only mappings that passed validation for the exact SDK coordinate it advertises.

## Registry Submission and Publication

A registry contribution follows one path:

1. Add or update the single maintained mapping artifact.
2. Add or update only the focused fixtures needed to prove its rules.
3. Select one or more exact SDK versions for validation.
4. Run schema, extension, SDK-surface, positive-fixture, and negative-fixture checks in registry CI.
5. Review the compact authored rule diff and expected Condition changes.
6. Publish an immutable mapping release.
7. Generate a validation attestation for each exact SDK version that passed.
8. Regenerate and sign the ecosystem catalog.

The pull request does not contain generated catalog diffs, generated mapping expansions, historical evidence reports, or a prose document unless a registry-wide contract itself changes.

## SDK Release Maintenance

For each package with a registry mapping, registry automation observes new SDK releases and tests the latest accepted mapping against the new exact version.

### Compatible release

If symbol, parameter, extension, and fixture validation pass:

1. retain the existing mapping release unchanged;
2. publish a new validation attestation associating that mapping digest with the new SDK version; and
3. update the generated catalog.

No mapping edit or human-authored maintenance document is required.

### Incompatible release

If validation fails:

1. do not advertise a mapping for the new SDK version;
2. report the specific missing or changed rule, symbol, parameter, or fixture result;
3. update only the affected mapping rules and fixtures;
4. publish a new immutable mapping release after review; and
5. validate the new release against the affected SDK versions.

The registry must not fabricate compatibility, silently reuse a failed mapping, or require a complete SDK-surface audit.

### Extension change

An existing mapping continues to target its immutable extension release. Moving to a new extension release requires an intentional mapping update, new validation, and a new mapping release. SDK releases alone do not change extension vocabulary.

## Review Surface

Human review is limited to:

- changed source-pattern match rules;
- changed Condition identity bindings;
- changed extension writes;
- the extension release selected by the mapping;
- concise positive and negative fixture results; and
- the exact SDK versions validated for publication.

Catalogs, digests, attestations, caches, bundles, and package indexes are generated and verified automatically.

## First Implementation Sequence

Implementation proceeds in this order:

1. Add the optional S3 `bucketName` vocabulary in a new immutable S3 extension release.
2. Define the minimal SDK mapping schema around the eight rule constructs in this document.
3. Reuse the generic `writes[]` evaluator required by extension binding generation.
4. Implement Python symbol, argument, produced-surface, receiver, and static-identity evaluation.
5. Author the compact boto3/S3 mapping for direct `put_object`, managed `upload_file`, and resource `Bucket.put_object`.
6. Add the dynamic-service negative fixture and two-bucket identity fixture.
7. Implement mapping validation against exact boto3 releases.
8. Implement the central registry source layout, immutable publication, exact-version attestations, and generated Python catalog.
9. Connect the explicit `mappings resolve` command to that catalog and cache.
10. Run the unchanged application fixtures through `profile generate` without any research-era mapping artifacts.

No later step begins by inventing a new document or artifact layer. A missing implementation detail is resolved in the schema, code, tests, or this plan.

## Acceptance Criteria

The first iteration succeeds only when:

- an SDK mapping author can understand and edit the complete boto3/S3 mapping as one compact file;
- `put_object`, `upload_file`, and the resource API emit extension-valid Conditions;
- `upload_file` writes the agreed conservative canonical operation set directly;
- two statically distinguishable buckets emit two Conditions;
- a known bucket name is optional and emitted only when statically proven;
- a dynamic service selection emits no inferred Condition;
- no recursive SDK mappings or service-authoring artifacts are required;
- a compatible boto3 release can reuse the same immutable mapping through a generated validation attestation;
- an incompatible release produces a focused rule-level failure;
- the central catalog is generated rather than maintained by hand; and
- end users obtain registry mappings only by explicitly running `mappings resolve`.

If meeting these criteria requires restoring the archived research workflow, the implementation has failed and the mapping contract must be simplified rather than adding another layer.
