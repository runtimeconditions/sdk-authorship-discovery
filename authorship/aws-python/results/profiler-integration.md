# AWS Python profiler integration review

## Outcome

The real Python profiler now consumes the owner-aligned boto3, botocore, and s3transfer mappings and profiles all seven unchanged AWS application fixtures. It discovers installed distribution metadata without importing the SDK, verifies each mapping file and semantic digest, resolves owner-qualified mapping references, validates emitted Conditions against the exact AWS S3 extension release, and preserves the existing declarative-binding and Kubernetes behavior. The proof now runs through the installed profiler command against mappings loaded from three rebuilt wheels rather than relying only on an in-process test catalog.

## Acceptance results

| Application | Proven source flow | Profile result |
| --- | --- | --- |
| `direct-client` | Literal `boto3.client("s3")` factory to botocore client method | `PutObject` bucket condition |
| `session-client` | Imported service-name constant through `boto3.Session.client` | `PutObject` bucket condition |
| `factory-wrapper` | Cross-module application function returning the mapped client | `PutObject` bucket condition |
| `dependency-injection` | Mapped client passed into an application constructor, stored on an instance, and called through a protocol-shaped field | `PutObject` bucket condition |
| `resource-api` | `boto3.resource("s3")` to `ServiceResource.Bucket` relation and `Bucket.put_object` action | `PutObject` bucket condition |
| `dynamic-service` | Runtime service selector passed through an application factory | No inferred extension or condition |
| `managed-transfer` | boto3 client wrapper through an owner-qualified s3transfer call and terminal botocore operations | One bucket condition containing the five mapped managed-upload operations |

The exact generated profiles are under [`profiles`](profiles/). They are regression-tested outputs rather than hand-maintained examples.

## Mapping constructs now consumed

The implementation consumes mapping vocabulary rather than hard-coding boto3 or S3 symbols. It supports client and resource factories with literal service selectors, SDK aliases, terminal generated-client methods, owner-qualified `operationRef`, resource relations and actions, client and resource `callRef` wrappers, owner-qualified s3transfer calls, and their terminal operation paths. Application data flow currently covers imported constants, relative imports, cross-module function returns, direct constructors, session objects, application constructors, instance fields, and bound application methods.

Tests and generated package metadata are excluded from workload source discovery. This is essential to the dynamic-service result because its test legitimately constructs an S3 client with a literal service name while its application source does not prove that the runtime service selector is S3.

## Managed-transfer policy

The application proves that the boto3 managed-upload wrapper will require an S3 bucket, but its source does not select classic versus CRT behavior or single-part versus multipart execution. The profiler therefore composes every operation reachable from the mapping's declared managed-upload implementations and execution paths: `PutObject`, `CreateMultipartUpload`, `UploadPart`, `CompleteMultipartUpload`, and failure-recovery `AbortMultipartUpload`.

This is an explicit conservative capability policy. It does not add an unproven resource condition, but it can request more permissions than one particular runtime execution uses. Emitting nothing would discard a certain S3 dependency, while selecting one path would fabricate runtime evidence. It is approved for this experiment because the emitted operations are concrete and actionable extension vocabulary, unlike a higher-level intent whose adapter interpretation could vary. The experiment does not treat this decision as a universal cross-SDK rule; future SDK owners should challenge it against their own mutually exclusive execution paths.

## Registry-free release proof

The full baseline proof rebuilt official boto3 1.43.70, botocore 1.43.70, and s3transfer 0.19.2 source at commits `8c2ae687338ebadf80dfd92114e12708304a545d`, `144a686dde0a37b694e6b67e073a9c8b4bbc4afe`, and `467a75265eca43937a760c2c169488954df44246`. It staged the current YAML mappings and semantic digests, built three wheels, installed them by local path into a clean Python 3.12 target, discovered their metadata, ran all seven application test suites, invoked the real profiler command seven times, and semantically compared every generated YAML profile with its accepted result. All 49 recorded stages passed.

Paired builds of the same unmodified and mapped source in the same environment measured a current compressed increase of 10,441 bytes:

| Wheel | Unmodified | With current mapping | Increase |
| --- | ---: | ---: | ---: |
| boto3 | 140,127 B | 144,047 B | 3,920 B |
| botocore | 15,594,015 B | 15,598,444 B | 4,429 B |
| s3transfer | 90,318 B | 92,410 B | 2,092 B |

## Release-maintenance gate

Full historical and ongoing maintenance runs now check out an explicit Python profiler revision, record that revision beside the SDK and extension revisions, profile all seven applications from the freshly built wheel installation, and retain the generated profiles in run evidence. Profile comparison is semantic YAML comparison, so formatting-only changes do not create maintenance work. A profiler command failure, invalid output, missing expected profile, or semantic mismatch stops as an `invalid` integration result; it is not automatically classified as SDK-author work. Static-only runs continue to exercise extension, generation, mapping, and source gates without requiring the profiler consumer.

## SDK-author impact

No new AWS SDK annotation, SDK source edit, runtime dependency, or application declaration was introduced for profiler consumption. The three deterministic mapping generators now add a semantic digest over their generated operation and Python bodies, and the staging, installed-discovery, owner-graph, and profiler gates independently verify it. This is generated integrity metadata rather than a new maintainer-authored concept.

The seven application fixtures, accepted profiles, and cross-repository consumer gate belong to this Runtime Conditions experiment. They are not proposed as seven files that boto3, botocore, or s3transfer maintainers must own. An upstream SDK integration would generate and package its owned mapping and run the focused source and artifact gates; Runtime Conditions consumer compatibility can remain in Runtime Conditions CI or another integration-test lane unless an SDK project voluntarily chooses to adopt it.

## Current boundaries

This experiment does not make the Python analyzer a complete Python type or control-flow engine. It intentionally emits nothing when the factory service cannot be resolved to a literal. Paginators, client waiters, resource collections, transfer-class entrypoints, branch predicates, identity extraction into profiles, independently selected execution paths, and arbitrary dependency-injection frameworks remain outside the proved profiler surface. The AWS S3 extension also does not currently place bucket identity in the emitted Condition, so mapping identity paths are validated authoring evidence but are not profile fields.

The implementation establishes a second, materially different SDK mapping consumer architecture alongside Kubernetes. Common profiler vocabulary should be extracted from both, while their generated-client and composed-factory constructs remain distinguishable rather than forced into one representation.
