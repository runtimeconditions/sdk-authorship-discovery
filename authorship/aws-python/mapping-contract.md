# Recursive SDK mapping contract

This document records the contract implemented by the AWS SDK for Python authorship proof. The implementation is real and validated, while cross-language standardization remains future work.

## Serialization

Every Runtime Conditions-owned SDK mapping, distribution index, generator manifest, maintenance state, and evidence document is serialized as YAML with a `.yaml` suffix. First-party tools may parse JSON only when an authoritative upstream SDK or service model is published in JSON; that input boundary does not permit Runtime Conditions tooling to emit JSON. JSON Schema remains the schema vocabulary embedded in extension definitions and is independent of artifact serialization.

## Distribution index

Every owning Python distribution packages one index at a path ending in `runtimeconditions/index.yaml`.

```yaml
apiVersion: runtimeconditions.io/sdk-mapping/v1alpha1
kind: RuntimeConditionsSDKMappingIndex
metadata:
  distribution: boto3
  distributionVersion: 1.43.70
  language: python
mappings:
  - name: boto3.aws.s3
    service: s3
    path: boto3/runtimeconditions/mappings/aws-s3.yaml
    sha256: ...
```

A consumer finds this index through installed-distribution metadata rather than importing the package. The index version and every indexed mapping version must equal the installed distribution version. The digest protects index-to-mapping integrity; it is not an application compatibility lock.

## Mapping identity

Every mapping has an owner-qualified identity and uses the SDK mapping API independently of the profile or extension document API:

```yaml
apiVersion: runtimeconditions.io/sdk-mapping/v1alpha1
kind: RuntimeConditionsSDKMapping
metadata:
  name: boto3.aws.s3
  distribution: boto3
  distributionVersion: 1.43.70
  language: python
  service: s3
  semanticSha256: 0e7942c78cf4d835f8189e62597d907a311422852b929d7fa2c85fcb2a3a8804
```

`apiVersion` versions the mapping document schema. `metadata.distributionVersion` identifies the exact SDK artifact that owns its public bindings. Neither is the semantic version of an extension. `metadata.semanticSha256` is deterministically calculated from the generated `operations` and language body; staging, installed discovery, graph validation, and profiler consumption recompute it rather than trusting the recorded value.

## Dependencies

An SDK mapping dependency names another owner-qualified mapping:

```yaml
kind: sdkMapping
distribution: botocore
mapping: botocore.aws.s3
```

A terminal service mapping uses an extension dependency to select one immutable semantic release and includes all three verification coordinates:

```yaml
kind: extension
id: https://runtimeconditions.io/extensions/aws-s3/0.1.0/runtimeconditions.extension.yaml
version: 0.1.0
semanticSha256: 1a505b63d55893c26f3ffe6cf3cd9f90f0b5bd7975fabe47ff444a3ed1e13c72
```

The ID is immutable, the version expresses the extension maintainer's semantic release, and the digest prevents content substitution. Many SDK distributions and releases may target the same extension release. A terminal SDK mapping must be regenerated or rejected if it claims a different extension identity or digest than the language-neutral service mapping it consumes; higher-level mappings inherit that terminal contract through owner-qualified dependencies.

SDK mapping dependencies form a directed acyclic graph. A cross-owner reference must also be declared as a dependency. The graph does not repeat the complete software dependency graph: transport, serialization, retry, and utility packages become mapping nodes only when their owned public behavior introduces a meaningful external-resource semantic step or another Runtime Condition.

No SDK compatibility range appears in this graph. Ordinary package dependency resolution selects the installed SDK versions; discovery then requires each selected package to supply metadata for its exact installed version.

## Typed references

The proof uses three owner-qualified reference types:

```yaml
operationRef:
  distribution: botocore
  mapping: botocore.aws.s3
  operation: PutObject
---
waiterRef:
  distribution: botocore
  mapping: botocore.aws.s3
  waiter: bucket_exists
---
callRef:
  distribution: s3transfer
  mapping: s3transfer.aws.s3
  call: managed-upload
```

Consumers resolve the declared distribution and mapping before member lookup. Names are not global and are never resolved by best match.

## Canonical operations and SDK aliases

The language-neutral service mapping owns one template set per canonical operation in the selected extension release. A language SDK mapping binds its public members to that canonical set.

An SDK may expose compatibility names absent from the authoritative service model. Those names are explicit SDK annotations and resolve to a canonical operation; they do not add extension vocabulary. In the current proof, 116 botocore client methods resolve to 112 canonical S3 operations through four aliases.

## Public construction and call surfaces

Factory mappings contain every public symbol or alias the owning SDK exposes, positional and keyword selectors, accepted service values, and produced surfaces. Resource mappings retain identifiers, actions, relations, collections, waiters, returned resources, and argument propagation.

Handwritten wrapper bindings normalize their public arguments before referring to an underlying logical call:

```yaml
method: upload_file
receiverArguments:
  bucket: Name
arguments:
  fileobj:
    position: 0
    keyword: Filename
  key:
    position: 1
    keyword: Key
callRef:
  distribution: s3transfer
  mapping: s3transfer.aws.s3
  call: managed-upload
```

Positions exclude the receiver. Both positional and keyword forms are recorded because application source can use either. Source validation rejects a binding when its owning signature changes.

When behavior depends on state supplied during object construction, a method binding includes `receiverContext` with its constructor symbol and argument binding. This retains transfer configuration for classic, CRT, and multipart reasoning even when a later public method receives no configuration parameter. The generator rejects a wrapper or entrypoint that binds a logical argument absent from its referenced call.

## Execution paths and predicates

A logical call may have multiple implementations and mutually exclusive paths. `selection` is a human-reviewable semantic description, not an instruction for a profiler to guess a branch. `when` and `whenAll` preserve predicates on optional follow-up calls. `usage` distinguishes always-on-path, one-or-more, zero-or-more, and failure-recovery calls.

These are behavioral facts about the SDK. They are not emitted profile fields, coverage metrics, or unresolved observations. If static analysis cannot select a path or prove a predicate, the profiler and its caller decide whether to omit, widen, warn, request a no-op declaration, or apply another policy. The current Python managed-upload fixture widens within one proven S3 bucket condition to every operation reachable through the mapped classic, CRT, single-part, multipart-success, and failure-recovery paths; this is an explicit experiment policy rather than a universal mapping rule.

## Extension boundary

Only the language-neutral botocore service mapping defines S3 Condition templates. Higher-level mappings reference canonical operations and cannot invent extension fields.

For `PutObject`, the terminal template is:

```yaml
kind: aws.s3
interfaceType: bucket
identity:
  source: input
  path: Bucket
operation:
  name: PutObject
```

This describes an S3 API operation, not an IAM action declaration. Authentication, environment variables, provisioning policy, and downstream incomplete-detection behavior remain outside the SDK mapping unless extension vocabulary defines them and application source proves them.

## Required consumer failures

The verifier fails closed for absent indexes or mappings; digest, distribution, or exact SDK version mismatches; duplicate mapping identities; absent or cyclic dependencies; undeclared cross-mapping references; missing referenced operations, waiters, or calls; noncanonical operation aliases; extension identity, version, or semantic-digest mismatch; and operation-to-Condition inconsistency.

Those are metadata integrity errors. They are distinct from incomplete application detection, whose policy remains outside the mapping layer.
