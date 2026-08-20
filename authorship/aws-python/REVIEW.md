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

The proof establishes first-time generation, package integration, recursive discovery, source validation, and unchanged application behavior for one real SDK dependency graph. It does not yet establish routine release automation, maintainer acceptance, a cross-language standard, or profiler consumption.

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
- Maintainers must not review generated mapping JSON line by line.
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

An SDK mapping does not define Runtime Condition vocabulary. It maps SDK behavior to Conditions already defined by an extension and must obey that extension's schemas. This makes an extension a prerequisite for an authoritative mapping, while keeping provisioning, credentials, platform policy, and incomplete-detection policy outside the mapping.

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
<package>/runtimeconditions/index.json
<package>/runtimeconditions/mappings/*.json
```

The index identifies the owning distribution, exact installed version, mapping identity, service, file path, and digest. Discovery reads package metadata and JSON without importing the SDK. The SDK does not import Runtime Conditions code and the application adds no runtime dependency.

## What has been implemented and proved

| Capability | Status |
| --- | --- |
| Generate canonical service semantics from an existing service model plus a reviewed semantic overlay | Proved |
| Generate language and SDK surfaces from existing resource models and focused wrapper annotations | Proved for the Python case |
| Split mappings across independently versioned behavior owners | Proved across three real Python distributions |
| Validate package versions, modeled inventories, generated names, handwritten signatures, bindings, and delegates against source | Proved |
| Validate owner-qualified references, declared dependencies, target members, Condition consistency, and graph cycles | Proved |
| Stage mappings into unmodified SDK source apart from static package-data declarations | Proved |
| Build and install local SDK wheels without registry publication | Proved |
| Discover installed mappings recursively without importing SDK modules | Proved |
| Preserve existing application behavior with the rebuilt SDK packages | Proved across seven application fixtures |
| Automatically react to new upstream releases | Not implemented |
| Classify release drift and create a concise maintainer review report | Not implemented |
| Publish official or community mapping artifacts continuously | Not implemented |
| Consume the mapping in a language profiler | Not implemented |
| Establish a cross-language mapping standard | Not decided |

The implementation used official boto3 1.43.70, botocore 1.43.70, and s3transfer 0.19.2 source. The generated metadata added 11,678 compressed bytes across the three wheels. The installed packages passed application regression tests, static discovery, recursive validation, and runtime-surface checks. No profiler was modified.

The evidence is recorded in [`results/2026-08-14-owner-aligned-packaging-rehearsal.md`](results/2026-08-14-owner-aligned-packaging-rehearsal.md).

## Can new releases trigger automatic mapping jobs?

Yes, the architecture and current generator/validator boundaries support that direction. No, the current repository is not yet an end-to-end continuously maintained system.

The existing tools already accept source models, source trees, versions, reviewed overlays, and output paths. They generate deterministic artifacts, reject owner/version mismatches, validate references, and stage metadata into package source. Those are the difficult core operations a release job needs.

What is still missing is the release-maintenance control plane:

- no workflow currently watches or receives releases from boto3, botocore, or s3transfer;
- no job obtains a new tag, selects the correct inputs, runs the full pipeline, and records the result;
- no classifier distinguishes a safe mechanical regeneration from a semantic change requiring review;
- no concise release report is generated for maintainers;
- no official or community publication path has been selected;
- no integration job validates a newly resolved compatible combination of the three independently released packages;
- the boto3 and s3transfer overlays currently contain exact expected-version fields, which would force meaningless edits on routine releases and therefore conflict with the intended maintenance experience.

The last point is important. Version identity belongs in generated metadata and must be checked against the source or built artifact. It should not normally be a human-maintained semantic-overlay change. Semantic fingerprints are different: when an operation set or meaningful behavior changes, the job should stop until that change is reviewed.

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

It would not rewrite generated SDK source, add Runtime Conditions runtime APIs, or ask maintainers to review the generated JSON.

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

The three reviewed example overlays are under [`../../../extensions/aws-s3/model`](../../../extensions/aws-s3/model/). The generated JSON should only be inspected for representative spot checks or to investigate a failed validation claim.

## The next step

The next step is a release-maintenance rehearsal, not another S3 feature expansion and not profiler integration.

The remaining adoption question is whether this architecture makes continuing SDK maintenance acceptably small and predictable. A repository watcher by itself cannot answer that question; it only starts a job. We first need a repeatable job that can process releases and demonstrate exactly when a maintainer is interrupted.

### Proposed milestone: repeatable mapping update runner

Build one maintainer-facing update runner that:

1. Accepts an owner repository and immutable release tag as input.
2. Obtains and verifies the source version without requiring a semantic-overlay version edit.
3. Regenerates only the mapping owned by that package.
4. Validates source surfaces, recursive references, package staging, and representative resolutions.
5. Compares the new release with the last accepted mapping inputs and outputs.
6. Classifies the result as automatic, review required, or unsupported/invalid.
7. Produces a concise Markdown review report containing the affected authored inputs, upstream source/model changes, counts, digests, diagnostics, and representative traces.
8. Emits deterministic artifacts suitable for a pull request or release job.

### Historical release test

Run the update runner across a sequence of real historical releases rather than only the versions used to build the proof. A useful first sample is at least ten consecutive boto3/botocore releases ending at the current proof version, plus every s3transfer release compatible during the same interval.

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
- maintainers never need to inspect the full generated JSON;
- generated artifacts remain version-aligned with their owning packages;
- the resolved multi-package graph validates;
- the application experience remains unchanged;
- the release report is understandable enough to use in an SDK maintainer interview.

After this rehearsal, the same runner can be connected to an SDK-owned release workflow or a community upstream watcher. The measured reports should then be taken to boto3, botocore, and s3transfer maintainers to test whether the burden and diagnostics are acceptable. Only after that feedback should the candidate contract be revised or frozen for a first profiler-consumption prototype.

## Decisions intentionally deferred

- Whether official metadata ships inside normal SDK artifacts or in automatically installed companion artifacts.
- The governance and precedence rules when SDK-owned and community mappings both exist.
- The final cross-language vocabulary for recursive calls, receiver state, and execution paths.
- The portable predicate language needed when a wrapper can select multiple runtime paths.
- Profiler behavior when application source cannot prove a mapping branch.
- Expansion to other AWS services and other programming languages.
- The all-services Smithy workflow recorded in [`../../../todos/aws-smithy-all-services-generator.md`](../../../todos/aws-smithy-all-services-generator.md).

## Recommended review order

1. Read this document for the adoption, authorship, ownership, maintenance, and next-step model.
2. Review the concrete SDK-author instructions in [`../../../extensions/aws-s3/docs/sdk-author-workflow.md`](../../../extensions/aws-s3/docs/sdk-author-workflow.md).
3. Review the candidate consumer and packaging contract in [`mapping-contract.md`](mapping-contract.md).
4. Review the three human-authored overlays under [`../../../extensions/aws-s3/model`](../../../extensions/aws-s3/model/) to judge their burden.
5. Review the measured proof in [`results/2026-08-14-owner-aligned-packaging-rehearsal.md`](results/2026-08-14-owner-aligned-packaging-rehearsal.md).
6. Consult S3-specific design and validation documents only where needed to verify a claim.
7. Finish with the maintainer questions and design red lines in [`../../docs/sdk-author-experience.md`](../../docs/sdk-author-experience.md).

## Current status in one sentence

The work proves a viable first-time SDK mapping authorship and packaging model; the next necessary proof is that real releases can be regenerated automatically while interrupting maintainers only for small, genuine semantic changes.
