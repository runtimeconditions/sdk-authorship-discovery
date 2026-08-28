# SDK authorship architecture review

## Purpose and scope

This is the canonical review brief for the SDK mapping investigation. Its subject is the experience of adopting, authoring, packaging, and maintaining SDK mappings. AWS S3 and the AWS SDK for Python are the implementation used to test the architecture; their service-specific details are evidence, not the center of the proposal.

The detailed AWS S3 extension design, operation classification, transfer paths, generated mappings, and validation records remain available in the supporting documents. A reviewer should only need those details when testing a claim made here.

## Executive conclusion

The implementation supports a credible candidate architecture with five defining properties:

1. Application developers use and version an SDK normally. Recognized SDK calls require no Runtime Conditions dependency, annotation, mapping file, evidence file, or compatibility lock.
2. SDK maintainers author only semantics that cannot be derived safely from models or source. The large static mappings are generated and are not a human review surface.
3. Mapping ownership follows the package that versions the public behavior. Mappings can therefore compose recursively across packages without one package claiming authority over another package's behavior.
4. Static metadata ships with its owning SDK artifact, or with a version-aligned companion artifact, and can be discovered without importing or executing the SDK.
5. Routine releases should regenerate automatically. Changes that may alter Runtime Condition meaning must stop with a focused maintainer review rather than being accepted silently.

The proof establishes first-time generation, package integration, recursive discovery, source validation, unchanged application behavior, authoritative extension maintenance, historical SDK replay, ongoing SDK release observation, and real Python profiler consumption for one dependency graph. It does not yet establish maintainer acceptance, a cross-language standard, or official artifact publication.

## Product constraints

### Application developers

- The application developer must have the best first experience.
- A mapped application should use normal SDK code and run the profiler locally or in CI.
- Recognized SDK calls should require no Runtime Conditions-specific application work.
- False Conditions are more damaging than incomplete detection because they can cause unnecessary permissions, resources, cost, and orphaned infrastructure.
- Extension-provided no-op bindings and project-local overrides remain the fallback for missing or incomplete detection.
- Ordinary output should stay concise. Detailed evidence belongs behind verbose tooling.
- The mapping layer does not publish coverage percentages or unresolved observations. Tooling, organizations, platform teams, and adapters decide how incomplete detection is handled.

### SDK authors and maintainers

- No significant SDK rewrite is acceptable.
- Generated SDK source must not be edited by hand.
- Canonical service semantics should be authored once rather than reproduced in every generated language.
- An ordinary SDK release must not require an ordinary handwritten mapping edit.
- Maintainers must not review generated mapping YAML line by line.
- Mapping support must not add Runtime Conditions code to the SDK's runtime path.
- Validation failures must identify the small authored input or upstream behavior that requires attention.

### Participation and governance

- SDK owners and community maintainers may both create mappings.
- SDK-owner participation is desirable and SDK owners can be solicited as first adopters, but their participation cannot be assumed.
- A mapping adopted by an SDK repository follows that repository's governance and release lifecycle.
- A community mapping must state what package and versions it targets and must not falsely claim SDK-owner authority.
- “Owner-aligned” means aligned with behavioral and version authority; it does not restrict who may propose or maintain the mapping.

The living constraints are recorded in [`../../docs/product-constraints.md`](../../docs/product-constraints.md) and [`../../docs/sdk-author-experience.md`](../../docs/sdk-author-experience.md).

## Architecture under review

### Extension alignment

An SDK mapping does not define Runtime Condition vocabulary. It maps SDK behavior to Conditions already defined by an exact immutable extension release and must obey that extension's schemas. The current contract verifies the extension identifier, semantic version, extension semantic digest, and language-neutral service-mapping digest while keeping provisioning, credentials, platform policy, and incomplete-detection policy outside the mapping.

### Three input classes

The implementation separates three kinds of information:

| Input | Source | Review expectation |
| --- | --- | --- |
| Mechanically knowable SDK structure | Existing service models, resource models, generated names, and source signatures | Generated and validated automatically |
| Runtime Condition meaning | Small extension-aligned semantic overlays | Reviewed when meaning changes |
| Static mapping artifacts | Deterministic projection of the first two inputs | Validated and summarized, not reviewed line by line |

This separation is the main authorship proposition. A mapping system that asks maintainers to reproduce machine-known SDK structure manually has failed the adoption requirement even if its output is technically correct.

### Behavioral ownership and recursive composition

The AWS Python case demonstrated that the package imported directly by an application may not own all behavior reached through its public methods. boto3 accepts independently versioned botocore and s3transfer packages, so a single mapping versioned only with boto3 would misstate who owns low-level operations and managed-transfer behavior.

The candidate therefore gives each distribution a mapping for the behavior it versions and uses owner-qualified references between mappings:

```text
higher-level public SDK surface
  -> mapping owned by that package
  -> lower-level semantic call owned by another package, when applicable
  -> extension-defined Runtime Condition
```

Recursion follows semantic behavior, not the complete software dependency graph. A transport, serializer, retry helper, or utility library does not become a mapping node merely because it executes. A dependency becomes another node only when its owned behavior adds a meaningful service/resource step or a separate Runtime Condition.

The proposed reference, dependency, index, discovery, and failure semantics are specified in [`mapping-contract.md`](mapping-contract.md).

### Static delivery

Each owning Python distribution packages a small index and one or more static mapping files:

```text
<package>/runtimeconditions/index.yaml
<package>/runtimeconditions/mappings/*.yaml
```

The index identifies the owning distribution, exact installed version, mapping identity, service, file path, and digest. Discovery reads package metadata and YAML without importing the SDK. The SDK does not import Runtime Conditions code and the application adds no runtime dependency.

## What has been implemented and proved

| Capability | Status |
| --- | --- |
| Generate canonical service semantics from AWS's authoritative public Smithy model plus a reviewed external Smithy overlay | Proved |
| Generate language and SDK surfaces from existing resource models and focused wrapper annotations | Proved for the Python case |
| Split mappings across independently versioned behavior owners | Proved across three real Python distributions |
| Validate package versions, modeled inventories, generated names, handwritten signatures, bindings, and delegates against source | Proved |
| Validate owner-qualified references, declared dependencies, target members, Condition consistency, and graph cycles | Proved |
| Stage mappings into unmodified SDK source apart from static package-data declarations | Proved |
| Build and install local SDK wheels without registry publication | Proved |
| Discover installed mappings recursively without importing SDK modules | Proved |
| Preserve existing application behavior with the rebuilt SDK packages | Proved across seven application fixtures |
| Process configured immutable historical releases automatically | Implemented through a manually triggered historical workflow and exercised against ten releases |
| Observe ongoing upstream releases and accepted extension semantic changes | Implemented through a scheduled workflow with durable evidence and focused review routing |
| Classify extension drift, SDK drift, and automation failure separately | Implemented and exercised through both maintenance lanes |
| Publish official or community mapping artifacts continuously | Not implemented |
| Consume the mapping in a language profiler | Proved across seven unchanged applications, including nested owner mappings and deliberately unresolved dynamic selection |
| Establish a cross-language mapping standard | Not decided |

The current packaging proof used official boto3 1.43.70, botocore 1.43.70, and s3transfer 0.19.2 source. Paired Python 3.12 builds of the same unmodified and mapped source measured a 10,441-byte compressed increase across the three wheels, including the generated semantic-digest fields. The full registry-free run passed 49 stages: generation and graph validation, three wheel builds, clean installed discovery, runtime and dependency checks, seven application test suites, seven real profiler invocations, and seven semantic YAML profile comparisons. The first hosted ongoing observation resolved and fully validated boto3 1.43.79, botocore 1.43.79, and s3transfer 0.19.2 against the same extension release with no semantic mapping change, but that run predates the newly added profiler gate. The consumer behavior and limits are reviewed in [`results/profiler-integration.md`](results/profiler-integration.md).

The evidence is recorded in [`results/2026-08-14-owner-aligned-packaging-rehearsal.md`](results/2026-08-14-owner-aligned-packaging-rehearsal.md).

## Can new releases trigger automatic mapping jobs?

Yes. The repository now contains a daily upstream observer that resolves a real boto3-rooted dependency graph from official tags and boto3's source-declared dependency ranges, regenerates the three owner mappings, validates their exact extension dependency, optionally builds and installs local wheels, runs the application fixtures, and records a durable observation.

The existing tools already accept source models, source trees, versions, reviewed overlays, and output paths. They generate deterministic artifacts, reject owner/version mismatches, validate references, and stage metadata into package source. Those are the difficult core operations a release job needs.

The historical and ongoing control planes obtain immutable tags, derive and validate source versions, check the selected dependency tuple against source declarations, regenerate and validate owner mappings, classify the release, optionally build and install the owner graph, run application fixtures, and emit machine-readable and maintainer-facing reports. Exact SDK versions are derived from source and remain enforced in generated metadata, staging, and installed discovery; they are not handwritten semantic-overlay changes.

What remains missing is an official or community publication path, evidence across a genuine SDK semantic interruption, independent observation of packages that cannot participate in a valid boto3-rooted graph, and maintainer feedback. The observer creates a focused pull request containing evidence and state for automatic or review-required outcomes and a deduplicated issue for review-required or invalid outcomes. It never silently approves new Runtime Condition semantics.

### SDK-owned automation

If the mapping is accepted into an SDK repository, the cleanest integration is not an external watcher. The repository's normal tag or release workflow should run its mapping projection and validation for the behavior that repository owns, then include the generated static files in the ordinary release artifact or an automatically installed companion artifact.

### Community-maintained automation

If the mapping remains external, the community repository needs an upstream event source. A scheduled job can poll upstream releases, or a webhook/GitHub App can send a repository dispatch when a release is published. GitHub documents repository-local events, scheduled triggers, and `repository_dispatch` for events originating outside the workflow repository in [Workflows](https://docs.github.com/en/actions/concepts/workflows-and-actions/workflows) and [Events that trigger workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows).

The community job should build a candidate update and open a reviewable change. It should not silently approve new Runtime Condition semantics. After repeated evidence shows that a class of changes is purely mechanical, that class could be eligible for automatic merge or publication under the community project's governance.

### Expected release flow

```text
new SDK release or tag
  -> obtain immutable source and verify its version
  -> load the previously accepted semantic inputs
  -> regenerate owner mapping
  -> validate source, references, packaging, and representative resolutions
  -> classify the result
     -> no semantic drift: produce an automatic artifact update
     -> semantic drift: produce a focused review request
     -> unsupported or invalid drift: fail closed with diagnostics
  -> validate the resolved multi-package graph
  -> publish only after the applicable repository gates pass
```

This is scalable because each package job owns only its layer. boto3 releases do not require botocore or s3transfer semantics to be copied into boto3, and a botocore service-model change does not require a handwritten operation-table change in every language.

## Maintainer experience implied by the candidate

### First integration

An SDK repository would:

1. Adopt or author the extension-aligned semantic input for the behavior it owns.
2. Add focused annotations for public handwritten behavior that existing models do not describe.
3. Enable deterministic mapping generation in its existing model or code-generation workflow.
4. Add static mapping files to the package build.
5. Add source, reference, and representative-resolution gates.
6. Review authored semantic changes and concise generated summaries.

It would not rewrite generated SDK source, add Runtime Conditions runtime APIs, or ask maintainers to review the generated YAML.

### Routine maintenance

- A release with unchanged semantics should regenerate with no human-authored change.
- A generated symbol or resource-model change should be handled mechanically and verified against source.
- A new service operation or a changed semantic scope should stop with a focused semantic review.
- A changed handwritten wrapper signature or delegate should point to the affected annotation.
- A changed nested execution path should point to the affected logical call rather than requiring a review of the entire mapping.
- A new language should reuse canonical service semantics and generate its language surface from that SDK's model; it should not reproduce the service operation table manually.

Whether those focused reviews are actually acceptable is not proved by code. It requires SDK-author review and maintainer interviews.

## Application experience implied by the candidate

For a mapped call, the application developer:

1. Selects and versions the SDK normally.
2. Writes normal SDK code.
3. Runs the language profiler locally or in CI.
4. Reviews the generated profile when desired.

The application developer does not install or author mapping metadata when it ships with the SDK, add a Runtime Conditions runtime dependency, annotate a recognized call, maintain an evidence file, or manage another compatibility lock.

When mapping or static detection is absent, extension-provided no-op bindings and project-local overrides remain the intended escape hatches. Application developers should not be asked to become SDK mapping authors.

## Why the AWS S3 case was sufficient evidence

S3 was valuable because it exercised more than a generated low-level client. The public application API crossed independently versioned packages, included generated and handwritten surfaces, carried constructor-held state into later calls, and could select different lower-level execution paths. That made it a strong test of authorship ownership and recursive composition.

Those mechanics should not dominate this review. The detailed service operation classifications, secondary resource paths, waiters, paginators, resource graph, multipart behavior, and CRT behavior are documented separately in:

- [`../../../extensions/aws-s3/docs/design.md`](../../../extensions/aws-s3/docs/design.md)
- [`../../../extensions/aws-s3/docs/api-analysis.md`](../../../extensions/aws-s3/docs/api-analysis.md)
- [`../../../extensions/aws-s3/docs/validation.md`](../../../extensions/aws-s3/docs/validation.md)
- [`../../../extensions/aws-s3/docs/sdk-author-workflow.md`](../../../extensions/aws-s3/docs/sdk-author-workflow.md)

The reviewed Smithy service overlay and the three SDK-specific annotation files are under [`../../../extensions/aws-s3/model`](../../../extensions/aws-s3/model/). The generated YAML should only be inspected for representative spot checks or to investigate a failed validation claim.

## Current maintenance experiment

The repeatable release-maintenance runner, manually triggered historical workflow, and scheduled ongoing-release workflow are implemented. The runner:

1. Accepts a configured historical tuple or a dynamically resolved compatible release tuple.
2. Obtains and verifies the source version without requiring a semantic-overlay version edit.
3. Regenerates each mapping in the selected owner graph from the accepted extension service mapping and SDK-owned inputs.
4. Validates source surfaces, recursive references, package staging, and representative resolutions.
5. Compares the new release with the last accepted mapping inputs and outputs.
6. Classifies the result as `automatic`, `extension-review-required`, `sdk-review-required`, or `invalid`.
7. Builds all seven acceptance profiles through an explicit Python profiler revision and compares their YAML semantics with the accepted application results.
8. Produces a concise Markdown review report containing the affected authored inputs, upstream source/model changes, counts, digests, diagnostics, representative traces, and profile comparison results.
9. Emits deterministic artifacts suitable for a pull request or release job.

### Initial historical result

The first sample ran ten consecutive boto3/botocore releases from 1.43.61 through 1.43.70 with s3transfer 0.19.2. All ten static runs were automatic, required no authored mapping change, and produced no semantic mapping difference from the accepted baseline. Full package and application verification also passed at 1.43.61, 1.43.69, and 1.43.70. The result and its limits are recorded in [`../../evidence/aws-python/2026-08-20-initial-historical-rehearsal.md`](../../evidence/aws-python/2026-08-20-initial-historical-rehearsal.md).

This result demonstrates a zero-touch routine-release path but does not test a genuine SDK semantic interruption or an s3transfer transition. The authoritative Smithy replay separately found 24 S3 model revisions and five operation-set transitions, establishing a real extension-review history without attributing that work to SDK maintainers.

### First ongoing result

On 2026-08-25 the resolver found boto3 1.43.79, botocore 1.43.79, and s3transfer 0.19.2 from official tags and boto3's declared ranges. All semantic, source, recursive graph, packaging, installed-discovery, runtime-surface, dependency, and seven application-fixture gates passed. The three mappings were semantically unchanged apart from their owner versions, so the observation was classified `automatic` and recorded under [`../../evidence/aws-python/ongoing`](../../evidence/aws-python/ongoing/). That hosted run predates the profiler acceptance gate now included in future full observations.

For each release, record:

- whether an authored overlay changed;
- whether the change was semantic or merely a version bump;
- what diagnostic a maintainer received;
- how large the review surface was;
- whether a valid package artifact was generated;
- whether the resolved three-package graph and application fixtures passed.

### Acceptance criteria

The milestone succeeds only if:

- releases with unchanged semantics require no handwritten mapping change;
- semantic changes fail closed and identify a small, relevant review surface;
- maintainers never need to inspect the full generated YAML;
- generated artifacts remain version-aligned with their owning packages;
- the resolved multi-package graph validates;
- the application experience remains unchanged;
- the release report is understandable enough to use in an SDK maintainer interview.

After the scheduled workflows produce clean hosted evidence and at least one genuine SDK review event, the measured reports and profiler integration should be taken to boto3, botocore, and s3transfer maintainers to test whether the burden, diagnostics, and consumer interpretation are acceptable. The current profiler is an implementation probe; the cross-language contract should not be frozen until that feedback and the remaining SDK cohort challenge it.

## Decisions intentionally deferred

- Whether official metadata ships inside normal SDK artifacts or in automatically installed companion artifacts.
- The governance and precedence rules when SDK-owned and community mappings both exist.
- The final cross-language vocabulary for recursive calls, receiver state, and execution paths.
- The portable predicate language needed when a wrapper can select multiple runtime paths.
- General profiler behavior when application source cannot prove a mapping branch beyond the explicit dynamic-service omission and the approved experiment-specific managed-upload widening decision.
- Expansion to other AWS services and other programming languages.
- Scaling the working external Smithy compiler from S3 to all services and integrating with AWS's internal Smithy/SDK generators, tracked in [`../../../todos/aws-smithy-all-services-generator.md`](../../../todos/aws-smithy-all-services-generator.md).

## Recommended review order

1. Read this document for the adoption, authorship, ownership, maintenance, and next-step model.
2. Review the concrete SDK-author instructions in [`../../../extensions/aws-s3/docs/sdk-author-workflow.md`](../../../extensions/aws-s3/docs/sdk-author-workflow.md).
3. Review the candidate consumer and packaging contract in [`mapping-contract.md`](mapping-contract.md).
4. Review the three human-authored overlays under [`../../../extensions/aws-s3/model`](../../../extensions/aws-s3/model/) to judge their burden.
5. Review the profiler behavior and boundaries in [`results/profiler-integration.md`](results/profiler-integration.md).
6. Review the earlier measured package proof in [`results/2026-08-14-owner-aligned-packaging-rehearsal.md`](results/2026-08-14-owner-aligned-packaging-rehearsal.md).
6. Consult S3-specific design and validation documents only where needed to verify a claim.
7. Finish with the maintainer questions and design red lines in [`../../docs/sdk-author-experience.md`](../../docs/sdk-author-experience.md).

## Current status in one sentence

The work now proves a viable authorship, packaging, extension-maintenance, and ongoing SDK-regeneration model; the next necessary proof is a genuine SDK review event and maintainer feedback on whether its interruption is small and understandable enough for adoption.
