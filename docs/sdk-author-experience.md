# SDK author experience

## Status

The owner-aligned AWS SDK for Python workflow is implemented and locally proved for S3, and the official Kubernetes Python client is implemented as the second model-generated architecture through extension release, exact generated and handwritten-wrapper mapping, local wheel packaging, installed discovery, unchanged application resolution, delegated condition transformation, and historical replay. Both remain under upstream maintainer review. The Python profiler now consumes both materially different mapping architectures without replacing its existing declarative-binding behavior; those contracts are not yet generalized across the remaining cohort.

The implementation, package patches, validation tools, measurements, and maintenance evidence are under [`../authorship/aws-python`](../authorship/aws-python/) and [`../maintenance/aws-python-s3`](../maintenance/aws-python-s3/). The earlier [`../authorship/boto3`](../authorship/boto3/) rehearsal is retained because it exposed the ownership flaw in a combined boto3 artifact.

## Current proposal

The extension owns canonical AWS S3 semantics and generates a language-neutral service mapping from AWS's authoritative Smithy model plus one reviewed external overlay. Each SDK distribution then maintains only the language surface and handwritten behavior it versions:

- botocore owns generated low-level client methods, SDK compatibility aliases, paginators, and waiters;
- boto3 owns factories, its resource model, aliases, and handwritten wrappers;
- s3transfer owns managed-transfer entrypoints and classic or CRT execution paths.

Mappings compose through owner-qualified `operationRef`, `waiterRef`, and `callRef` values. Every mapping version equals its owning installed distribution version. The terminal service mapping records the exact extension release and semantic digest; higher-level mappings inherit that relationship through validated dependencies. Ordinary dependency resolution selects package versions, so Runtime Conditions does not add another compatibility lock.

## Second generated architecture evidence

The Kubernetes Python 36.0.3 proof starts from the authoritative Kubernetes v1.36.2 OpenAPI model retained by the SDK repository, follows the SDK's transformed generator input, and statically verifies the generated synchronous and asynchronous sources. It joins 908 generated endpoints to authoritative Kubernetes operations and emits 28 separate generator-injected dynamic endpoint records without asking maintainers to author or review a 936-operation table. The exact extension digest, mapping, package, application, and historical evidence are under [`../authorship/kubernetes-python`](../authorship/kubernetes-python/).

This proof changes two architectural assumptions. Transformed operation IDs are reused across generated API classes, so an SDK mapping must identify a language symbol through its owning module/class and method or through its endpoint, not through an operation name alone. Kubernetes namespace access also requires distinct `namespaced`, `all_namespaces`, and `cluster` operation scopes; resource scope by itself is not enough to describe the demand observed at a call site.

The generated mapping contains 936 operation records, 1,873 public symbols, 132 explicit list-to-watch overrides, and one source-verified `Watch.stream` condition delegation. The rebuilt wheel adds 38,072 compressed bytes and one package-data declaration, and the profiler discovers the installed mapping without importing Kubernetes. The unchanged ConfigMap application emits `get configmaps`; the unchanged Pod watcher composes `Watch.stream` with `list_namespaced_pod` and emits `watch pods`. A direct list remains `list`, a wrapped log stream remains `get pods/log`, and an unresolved callable emits nothing. A mixed-source regression fixture preserves its existing declarative API and cache conditions while adding the mapped Kubernetes condition. `DynamicClient` and discovery-created resource delegation remain the deliberately visible boundary.

## First integration burden

The proved first-time steps are:

1. Select or help author an extension whose vocabulary represents the external service.
2. Enable the shared service-model projection or consume its accepted language-neutral output.
3. Add compact annotations for SDK compatibility aliases or public handwritten behavior absent from existing models.
4. Enable deterministic SDK mapping generation in the existing model or code-generation workflow.
5. Add static package-data paths for the generated index and mappings, or publish a version-aligned companion artifact.
6. Run source, extension-alignment, recursive-reference, and representative-resolution gates.
7. Review authored semantic changes and concise summaries rather than generated mapping files.

There is no Runtime Conditions runtime dependency, generated-client rewrite, or application-facing SDK API change. In the Python proofs, the only SDK build-source change is declaring the static package-data paths that contain the index and mapping.

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

The historical SDK sample processed ten releases from boto3/botocore 1.43.61 through 1.43.70 without an authored change. The first ongoing observation processed boto3 1.43.79, botocore 1.43.79, and s3transfer 0.19.2 through the then-current full package and application proof with no semantic mapping change. Future full observations also execute and compare the seven profiler acceptance profiles.

The historical Smithy inventory found 24 S3 model-changing commits and five operation-set transitions. That establishes a real extension-maintenance history and, importantly, prevents API-semantic work from being counted as SDK-author work.

The final Kubernetes Python generator can process v36.0.0 through v36.0.3 without per-operation semantic annotation or binding edits. That does not mean the experiment required zero authored work: building the initial integration was substantial work outside the replay's maintenance metric, and the initial retrospective replay then failed on v36.0.0. Supporting its synchronous-only generated surface required an authored projection change, review, and regenerated evidence. If integrated upstream, SDK maintainers would need to review and ship that tooling change even if Runtime Conditions contributors implemented it. Because the generator was developed against v36.0.3 and replayed backward, this result demonstrates current historical compatibility rather than chronological zero-touch production maintenance.

Prospective AWS maintenance outcomes are classified as `automatic`, `extension-review-required`, `sdk-review-required`, or `invalid`. The Kubernetes backward replay instead reports final compatibility and separately records observed investigative maintenance so an automation repair cannot masquerade as a zero-work result.

## Application experience

Application developers install and version the SDK normally. Mappings arrive inside packages already selected by dependency resolution or in a version-aligned companion artifact. For recognized calls, developers write no mapping file, evidence file, compatibility lock, no-op annotation, or Runtime Conditions runtime code.

The local AWS proof installed rebuilt wheels directly by path, discovered mappings without importing SDK modules, and profiled seven unchanged application fixtures through the real command. Paired builds measured a current 10,441-byte compressed increase across the three distributions, including the generated semantic-digest fields. Five ordinary object-upload shapes emit `PutObject`, the runtime-selected service fixture emits nothing, and managed upload composes the five concrete operations reachable through its mapped runtime paths. The latter widening is approved for this experiment because it is actionable extension vocabulary and avoids subjective higher-level intent, but it is not presumed to be a universal cross-SDK rule. The Kubernetes proof does the same for its generated typed-client and handwritten-wrapper mapping, unchanged ConfigMap and Pod watcher fixtures, and automatic Python profiler discovery at a compressed cost of 38,072 bytes.

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
8. Do Kubernetes Python maintainers consider the one package-data declaration and concise generated review acceptable in their release workflow?
9. Is one source-verified delegation annotation an acceptable maintainer representation of `Watch.stream`, and which team owns the remaining `DynamicClient`, discovery, and `Resource` behavior?

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
| 2026-08-26 | Adopt a sequential cross-architecture cohort of AWS Python, Kubernetes Python, NATS Go, OpenTelemetry Python, OpenFeature Go, and Dapr Java. | A convention cannot be presented as universal until it survives independently governed generated, handwritten, exporter, provider, and sidecar SDK models. |
| 2026-08-26 | Join generated Kubernetes Python methods by endpoint and owning language symbol rather than transformed operation ID alone. | Maintainers can generate mappings from their existing model and source while reused generator names remain unambiguous. |
| 2026-08-26 | Keep authoritative API semantics, transformed generator semantics, and public language symbols as separately verified layers. | Ordinary generation changes remain automatic while only dynamic or handwritten behavior enters the focused SDK-owned review surface. |
| 2026-08-26 | Publish the accepted local Kubernetes API 0.1.0 extension and bind the Python mapping to its exact semantic digest. | Generated records cannot invent Kubernetes vocabulary or silently target a moving extension. |
| 2026-08-26 | Keep 28 dynamic endpoints as separate method records and use shared rules only as generator implementation. | No combinatorial operation enters the mapping or application profile. |
| 2026-08-26 | Discover generated sync and async flavors per release instead of requiring both. | Retrospective replay required one authored projection repair. The repaired generator handles the sampled flavor transition without per-operation metadata, but the result must not be reported as zero-touch production maintenance. |
| 2026-08-27 | Represent `Watch.stream` as a condition delegation that composes with its callable target rather than as a standalone Kubernetes operation. | Maintainers review one source-verified wrapper annotation; generated API methods continue to own resource semantics, and unresolved delegates do not create broad conditions. |
| 2026-08-27 | Add installed SDK mapping discovery and delegated-call composition alongside the Python profiler's existing declarative bindings. | Application source remains unchanged, SDK code is never imported during profiling, exact package and extension metadata fail closed, and the prior profiler test suite remains a regression gate. |
| 2026-08-27 | Consume the three owner-aligned AWS mappings through the real Python profiler across all seven applications. | No new SDK annotations or application declarations are required; unresolved service selection emits nothing, while nested managed-transfer paths expose a concrete capability choice for explicit approval. |
| 2026-08-27 | Approve the concrete union of reachable managed-upload operations for the AWS experiment and add the seven accepted profiles to full release maintenance. | The result remains actionable and extension-defined without inventing a subjective high-level intent; profiler regressions fail as integration evidence rather than being assigned automatically to SDK maintainers. |
