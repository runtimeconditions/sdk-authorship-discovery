# SDK author experience

## Status

The owner-aligned AWS SDK for Python workflow is implemented and locally proved for S3. It remains an architecture under maintainer review; no profiler contract has been accepted and no profiler was changed.

The implementation, package patches, validation tools, measurements, and maintenance evidence are under [`../authorship/aws-python`](../authorship/aws-python/) and [`../maintenance/aws-python-s3`](../maintenance/aws-python-s3/). The earlier [`../authorship/boto3`](../authorship/boto3/) rehearsal is retained because it exposed the ownership flaw in a combined boto3 artifact.

## Current proposal

The extension owns canonical AWS S3 semantics and generates a language-neutral service mapping from AWS's authoritative Smithy model plus one reviewed external overlay. Each SDK distribution then maintains only the language surface and handwritten behavior it versions:

- botocore owns generated low-level client methods, SDK compatibility aliases, paginators, and waiters;
- boto3 owns factories, its resource model, aliases, and handwritten wrappers;
- s3transfer owns managed-transfer entrypoints and classic or CRT execution paths.

Mappings compose through owner-qualified `operationRef`, `waiterRef`, and `callRef` values. Every mapping version equals its owning installed distribution version. The terminal service mapping records the exact extension release and semantic digest; higher-level mappings inherit that relationship through validated dependencies. Ordinary dependency resolution selects package versions, so Runtime Conditions does not add another compatibility lock.

## First integration burden

The proved first-time steps are:

1. Select or help author an extension whose vocabulary represents the external service.
2. Enable the shared service-model projection or consume its accepted language-neutral output.
3. Add compact annotations for SDK compatibility aliases or public handwritten behavior absent from existing models.
4. Enable deterministic SDK mapping generation in the existing model or code-generation workflow.
5. Add static package-data paths for the generated index and mappings, or publish a version-aligned companion artifact.
6. Run source, extension-alignment, recursive-reference, and representative-resolution gates.
7. Review authored semantic changes and concise summaries rather than generated mapping files.

There is no Runtime Conditions runtime dependency, generated-client rewrite, or application-facing SDK API change. In the Python proof, the only SDK build-source change was adding two package-data paths per distribution.

The S3 review surface is one service-wide Smithy semantic overlay shared across languages, one four-entry botocore compatibility-alias file, one boto3 wrapper/factory annotation file, and one s3transfer behavior annotation file. Maintainers do not inspect the generated YAML mappings line by line.

## Recurring maintenance

The extension and SDK repositories have separate maintenance lanes joined by exact semantic coordinates:

| Change | Owner | Expected action |
| --- | --- | --- |
| Authoritative API model changes without Runtime Conditions semantic change | Extension automation | Validate automatically; retain the existing immutable extension release |
| New, removed, or reclassified API behavior | Extension stakeholders | Review the focused Smithy overlay difference and publish a new immutable extension release |
| Generated SDK names or modeled resources change without semantic drift | SDK automation | Regenerate and validate automatically |
| SDK-only compatibility alias changes | SDK maintainer | Update the small alias annotation |
| Handwritten wrapper signature, delegate, or execution path changes | Owning SDK maintainer | Update the focused wrapper or behavior annotation |
| Selected extension identity or digest does not match | Join gate | Reject the mapping before packaging or profiler use |

The historical SDK sample processed ten releases from boto3/botocore 1.43.61 through 1.43.70 without an authored change. The first ongoing observation processed boto3 1.43.79, botocore 1.43.79, and s3transfer 0.19.2 through the full package and application proof with no semantic mapping change.

The historical Smithy inventory found 24 S3 model-changing commits and five operation-set transitions. That establishes a real extension-maintenance history and, importantly, prevents API-semantic work from being counted as SDK-author work.

Maintenance outcomes are classified as `automatic`, `extension-review-required`, `sdk-review-required`, or `invalid`. The first two human routes identify the semantic owner; automation defects never masquerade as maintainer review.

## Application experience

Application developers install and version the SDK normally. Mappings arrive inside packages already selected by dependency resolution or in a version-aligned companion artifact. For recognized calls, developers write no mapping file, evidence file, compatibility lock, no-op annotation, or Runtime Conditions runtime code.

The local proof installed rebuilt wheels directly by path, discovered and digest-verified mappings without importing SDK modules, and passed seven unchanged application fixtures. The compressed package cost was 11,678 bytes across all three distributions.

When mapping support is absent or static detection is incomplete, extension-provided no-op bindings and project-local overrides remain the application escape hatch. Application developers should not be expected to author SDK mappings.

The mapping layer does not declare coverage percentages or unresolved observations. Developers, platform teams, profilers, CI policy, and downstream adapters decide how to handle incomplete detection.

## Participation and governance

SDK-owner and community mappings are both valid adoption paths. SDK owners should be solicited as first adopters, but participation cannot be assumed. A mapping adopted by an SDK repository follows that repository's governance and release lifecycle; an external artifact follows its publisher's governance and must identify its authority, target SDK versions, and target extension release accurately.

Owner alignment describes behavioral and version authority rather than company ownership. Anyone may propose metadata, but an artifact must not claim that one distribution versions public behavior owned by another.

## Design red lines

- No significant SDK rewrite.
- No independently handwritten operation table per language.
- No recurring handwritten edit for an ordinary generated release.
- No Runtime Conditions code in the application runtime path.
- No request that maintainers inspect generated mapping YAML line by line.
- No SDK mapping that invents extension fields, credential conventions, incomplete-detection policy, or adapter policy.
- No false implication that every mutually exclusive execution branch runs.
- No extension version bump caused solely by an SDK release or upstream provenance-only model change.

## Remaining maintainer interview questions

1. Is this four-input review surface acceptable, and which existing teams would own the service overlay, SDK aliases, boto3 wrappers, and s3transfer behavior?
2. Would normal SDK artifacts accept the package-data addition, or is an automatically installed version-aligned companion preferable?
3. Are `extension-review-required` and `sdk-review-required` diagnostics routed to the right people and precise enough for a release build?
4. Is the execution-path vocabulary faithful to how s3transfer maintainers reason about classic, CRT, multipart, cleanup, and conditional follow-up operations?
5. Which external Smithy traits could AWS adopt into its authoritative internal model, and which should remain community overlays?
6. What summary and representative fixtures would maintainers actually review when behavior changes?
7. Would maintainers permit automatic publication for `automatic` releases after enough evidence, or require a generated pull request for every release?

## Decision ledger

| Date | Decision | SDK-author impact |
| --- | --- | --- |
| 2026-08-13 | Treat existing SDK mapping conventions as disposable and optimize first for application adoption. | No prior manifest or profiler behavior constrains the design. |
| 2026-08-13 | Model AWS S3 with canonical operation objects aligned to an AWS extension. | SDK mappings preserve service calls; adapters own authorization translation. |
| 2026-08-14 | Split metadata across botocore, boto3, and s3transfer and compose it recursively. | Each package maintains only behavior it versions. |
| 2026-08-14 | Validate handwritten bindings and execution paths against pinned source. | Wrapper drift becomes a focused build error; the gate caught a real annotation defect. |
| 2026-08-20 | Derive exact SDK versions from immutable source instead of semantic overlays. | Routine releases do not create meaningless authored version-only edits. |
| 2026-08-20 | Add historical release replay and focused maintenance reports. | Ten consecutive releases regenerated without authored changes. |
| 2026-08-25 | Move canonical service semantics to AWS's authoritative public Smithy model plus an external overlay. | Service meaning is authored once and API changes are reviewed independently from language SDK changes. |
| 2026-08-25 | Use immutable extension releases and exact semantic digests as the one-to-many join. | Many SDK releases can reuse one extension release without a compatibility matrix. |
| 2026-08-25 | Add daily SDK observation with separate extension, SDK, and automation classifications. | Routine work is automated while focused semantic changes reach the correct maintainer. |
