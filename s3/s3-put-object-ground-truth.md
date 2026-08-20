# S3 PutObject Ground Truth

## Status

This document defines the product and semantic ground truth for the first SDK mapping investigation. It does not define a mapping schema and does not declare the existing AWS object-store example extension sufficient.

## Case

The baseline application contains:

```python
client = boto3.client("s3")
client.put_object(Bucket=bucket, Key=key, Body=body)
```

## What the application source establishes

For this direct case, static source analysis can establish:

- boto3 is the selected SDK package;
- the literal service identifier is `s3`;
- the receiver of `put_object` is the client created for that service;
- the code contains a call corresponding to the SDK's S3 `PutObject` operation;
- this client requires an S3 bucket Condition when a conforming SDK mapping connects the operation to an extension.

These claims still require verification against the resolved boto3 and botocore package versions and the SDK's shipped service model. The profiler must not execute application or SDK code to establish them.

## What the source does not establish

The call does not by itself establish:

- a concrete bucket name suitable for inclusion in the profile;
- an AWS account;
- a target region;
- a credential value;
- a credential delivery mechanism;
- environment variable names;
- whether this code path executes in every deployment;
- whether a target adapter will fulfill the requirement with AWS itself, LocalStack, or another compatible implementation.

The mapping must not invent these facts.

## Extension-owned semantics

The SDK mapping must target an existing extension. The extension determines whether and how the Condition represents:

- AWS S3 specifically or a broader S3-compatible object store;
- the `PutObject` operation;
- write access or permissions derived from that operation;
- an abstract bucket requirement;
- SDK-level authentication and configuration requirements;
- allowed configuration delivery mechanisms and property names.

The SDK mapper does not independently define those semantics. It selects and populates extension vocabulary, and the resulting Condition must validate against that extension.

The current example AWS object-store extension does not define operation vocabulary. It also demonstrates fixed environment-variable mappings that the baseline application does not establish. It must therefore be treated as an earlier example, not as the expected output contract for this investigation.

The current S3 extension candidate represents this requirement as:

```yaml
kind: aws.s3
interface:
  type: bucket
  operations:
    - name: PutObject
```

The canonical operation entry describes the S3 API call. It is not itself an
IAM authorization declaration; an adapter performs that translation.

## Expected Condition identity

Each statically distinguishable SDK client represents a separate Runtime Condition requirement.

This does not yet settle how static analysis defines a client identity when:

- one construction site is executed multiple times at runtime;
- a factory creates clients for several callers;
- aliases reference the same client;
- two clients are configured identically;
- client construction is hidden behind dependency injection.

The mapping architecture must define this without pretending static analysis can count arbitrary runtime instances. Until then, Conditions must not be semantically deduplicated merely because their extension fields are equal.

## Application fallback

If no conforming mapping is available, or the source pattern cannot be resolved conservatively, the application developer uses the no-op declaration package published by the chosen extension to declare the S3 bucket Condition explicitly.

The developer should not be asked to write a boto3 mapping. A project-local override may help a profiler understand an application abstraction, but it is not a substitute for the extension or its validation rules.

## Default and verbose experience

Ordinary profiling should emit the valid Condition without a committed evidence file or verbose provenance by default.

Verbose output should be able to explain:

- the client construction source location;
- the operation call source location;
- resolved boto3 and botocore versions;
- the SDK service-model operation;
- the selected mapping and its ownership;
- the target extension.

## Correctness rule

When service or client identity is ambiguous, do not emit the S3 Condition. An incomplete result with a remediation path is preferable to a false Condition that downstream automation may provision.

How a CI system detects or treats incomplete results is policy outside the mapping contract. The mapping layer does not publish coverage percentages or unresolved observations.
