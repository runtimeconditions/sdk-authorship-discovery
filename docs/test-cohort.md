# Cross-architecture SDK authorship test cohort

## Purpose

The SDK authorship architecture must work across independently governed SDKs with materially different construction, delegation, generation, packaging, and maintenance models. The AWS Python proof remains useful evidence, but it cannot establish a general SDK-authoring workflow by itself.

The cohort will be investigated sequentially. Each case must produce a detailed maintainer and application-adopter model before the next case is allowed to generalize its conclusions. Common contracts are extracted only from behavior demonstrated by at least two independent SDK families.

## Accepted cohort

| Case | Initial language | Architecture | Primary question |
| --- | --- | --- | --- |
| AWS S3 through boto3, botocore, and s3transfer | Python | Model-generated vendor SDK with handwritten wrappers and nested distributions | Can an authoritative service model, small SDK-owned overlays, and recursively packaged mappings remain aligned across releases? |
| Kubernetes official client | Python | OpenAPI-generated CNCF SDK | Does the generated workflow generalize beyond Smithy, and can it represent an extensible API without treating built-in resources as the entire platform? |
| NATS client | Go | Primarily handwritten direct integration | Can maintainers describe ordinary client behavior without maintaining an operation table or changing the public SDK? |
| MongoDB official drivers | Python and Go | Primarily handwritten language drivers governed by common specifications and backed by server IDL | Can one service authority support two idiomatic SDKs without duplicating service semantics, and can callbacks and wrappers enhance ordinary namespace demands? |

The MongoDB case begins in Python and Go together so cross-language reuse is tested before one implementation establishes the convention. Language choice is part of every case: the cohort must reveal the profiler contract each architecture actually needs. A profiler is not treated as frozen; any required change is reviewed explicitly and must preserve its existing regression suite.

OpenTelemetry exporters, OpenFeature providers, and Dapr sidecar delegation remain valuable architectural candidates. They are deferred because the investigation is now prioritizing broadly useful application SDKs, and their exact Runtime Conditions boundaries require additional product or maintainer discussion before they become the next implementation case.

## Sequence

1. Use the completed Kubernetes Python case as the second model-generated family and retain only the conclusions independently demonstrated by both it and AWS.
2. Complete the NATS Go case to test the authoring burden when there is no comprehensive service model from which to derive public behavior.
3. Investigate the MongoDB Python and Go drivers as one paired case, beginning with server-model authority and equivalent application fixtures before defining extension vocabulary or language mappings.
4. Select the next practical SDK only after the MongoDB case shows which conclusions generalize across two handwritten language APIs. Exporter, provider, and sidecar cases remain available when their Runtime Conditions product boundary is ready for review.

The cases are not implemented in parallel. Findings from a completed case may change the questions, fixture selection, or proposed artifacts for later cases.

## Common adoption gates

Every case must demonstrate the following before it can influence a general SDK mapping contract:

- An unchanged application installs and versions the SDK normally and requires no Runtime Conditions source declaration for a statically resolvable mapped call.
- SDK construction or configuration alone does not emit a condition when an external requirement has not been proven.
- The mapping targets an existing immutable extension release and cannot invent vocabulary, authentication conventions, environment variables, or adapter policy.
- Generated metadata is reviewed through concise semantic summaries; application developers and SDK maintainers are not asked to inspect generated mapping YAML line by line.
- Each repository owns only the behavior and version surface it publishes.
- Routine releases regenerate and validate automatically; human review is reserved for a focused extension-semantic or SDK-owned behavior change.
- The experiment records first-integration work, recurring work, generated artifact size, authored concepts, files added to the SDK repository, build and release integration points, and maintainer review time.
- The result is exercised against a real package release and at least one subsequent or historical release rather than accepted from a fixture-only demonstration.

## Generalization rule

A field or workflow demonstrated only by AWS remains an AWS hypothesis. A field demonstrated by two model-generated families may become a model-generated SDK convention. A contract presented as universal must survive the generated, handwritten, exporter, provider, and sidecar cases without transferring recurring complexity to application developers or SDK maintainers.

If an archetype genuinely requires additional metadata, the investigation will define an archetype-specific capability rather than forcing unrelated SDKs to populate meaningless fields.

## Current work

The AWS Python case has packaging, maintenance, and real profiler evidence across seven unchanged applications, including direct factories, application data flow, resources, nested transfer mappings, and unresolved dynamic selection. The Kubernetes Python case covers generated typed-client calls, dynamic generated endpoints, installed mapping discovery, one source-verified `Watch.stream` condition delegation, and one source-verified DynamicClient producer/state/method flow consumed without SDK imports or application declarations. NATS then established one shared service authority across handwritten Go and Python clients while exposing the remaining size of language-specific binding and state input. MongoDB is now active with eight paired Python and Go fixtures and an initial finding that public server IDL may avoid a fallback Operations Inventory for core commands; no MongoDB extension or SDK mapping has yet been approved.
