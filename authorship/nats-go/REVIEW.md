# NATS Go SDK authorship and profiler review

## Review status

**Classification: working two-language service-authority and real-profiler integration with an explicit and measurable SDK-author burden; not yet suitable to present as a finalized authoring experience.**

The official `nats.go` v1.53.1 source was staged locally with package-owned Runtime Conditions metadata. Six ordinary applications compiled against that staged module, and the real Go profiler produced extension-valid profiles for all six without Runtime Conditions declarations or configuration in application code. The comprehensive application exercises every operation form currently defined by the NATS extension and proves that two independently created connections remain separate Runtime Conditions.

This result proves more than the original NATS slice: exact named-parameter validation, typed struct-field binding, local configuration-value flow, state-only delegation, resource state propagation, dependency identity, safe condition grouping, deterministic surface classification, and fixture-level acceptance all work together. It also exposes authoring burden and extension gaps that should not be hidden by the successful profile output.

NATS now has a separate language-neutral Service Operations Inventory with 26 stable operations, an extension-owned Service Operations Semantic Bridge, and a generated service mapping. The inventory is the reviewed fallback service authority because this workflow has no adequate authoritative Smithy, OpenAPI, or equivalent NATS operation model; the bridge owns its Runtime Conditions translation. Both the Go and Python SDK integrations consume the same service mapping and exact semantic digest. Neither language overlay maintains canonical NATS Condition templates.

## The contract being tested

The extension and language-neutral service mapping supply the adapter-actionable semantics and stable operation identities. The SDK integration selects exact language symbols and binds extension fields to named parameters, typed fields, or prior producer state. The SDK's real function and type declarations validate those selections. The application supplies concrete values through ordinary source code. The profiler resolves only generic Go constructs and emits nothing when a required value or identity is not statically proven.

No layer invents another layer's facts. The extension does not name Go methods. The mapping does not define new extension actions. The profiler does not know NATS fields such as `Name`, `Bucket`, `Subjects`, or `Subject`. The application developer does not maintain SDK mappings.

The local-value addition is deliberately generic. A mapping can point to a named parameter and one typed field. If an application assigns a keyed struct literal directly with `:=` or an initialized local `var` declaration and passes that local to the mapped call, the profiler can resolve the selected field. Ordinary reassignment, field assignment, index assignment, or explicit address taking invalidates the remembered local value. Aliases, helper-function returns, values stored in structs or containers, control-flow joins that cannot be proven, and arbitrary data-flow are not resolved. This is a bounded language capability, not a NATS-specific `Name` lookup.

Producer state is also generic. A mapping may declare that a call creates a new dependency identity or inherits one from a receiver or state-bearing argument. Later calls can consume static fields from that producer state. The profiler groups compatible observations only when they target the same extension and condition shape and carry the same source-proven dependency identity. Calls without such proof stay separate.

## What an SDK maintainer would be asked to own

The current human-authored integration has 35 individual call descriptions and 20 grouped rules that expand to 52 additional methods. Together they generate 87 call records: 86 mapped public operations plus the state-only `jetstream.New` bridge. The input defines six state types, uses 54 operation references spanning all 26 canonical NATS operations, and is 892 lines of anchor-free YAML.

That size is a warning, not a success metric. Replacing authored Condition templates and YAML aliases removed the service-semantic duplication, but it reduced the overlay by only 71 lines, or approximately 7.4%, because SDK-specific binding and state structure still dominates. Call groups avoid individually repeating mechanically identical methods, but the present format remains too repetitive. Before asking NATS maintainers to adopt this, shared authoring tooling should derive more boilerplate, present a concise review diff, and keep the maintainer focused on SDK-specific decisions. We should evaluate the authority boundary as successful without normalizing an 892-line hand-reviewed file as the expected end state.

The public-surface policy is a second review surface. It covers 186 public symbols and requires every one to be mapped, explicitly excluded, or deferred. A normal release with no surface change should produce no review work. A new or changed operation should produce a focused classification request. The policy and its report are maintenance controls; the report is not published in an SDK mapping and the profile contains no coverage percentage or unresolved-observation list.

The intended division of responsibility is:

| Responsibility | SDK maintainer | Runtime Conditions tooling/project |
| --- | --- | --- |
| Decide how public SDK behavior aligns to reviewed extension semantics | Review and approve | Provide extension context and focused diffs |
| Classify a newly introduced public operation | Review and approve | Discover it and require a decision |
| Maintain parsers, generators, staging, integrity checks, and fixture orchestration | No | Yes |
| Review the generated mapping record by record | No | Generate and validate deterministically |
| Ship static metadata | Enable ordinary release packaging | Produce mapping and index |
| Add runtime code or a runtime dependency | No | Not applicable |

The two files added to an SDK release are one generated mapping and one small index. The experiment's coverage reports, fixture profiles, tools, and review documents are not package obligations.

## Cross-language service-authority result

The Go and Python integrations now record the same generated NATS service-mapping digest: `791de4f22212d2c6e61952a154ca6c1bd1904c6c430c766cb27680a8aeb01cb7`. The Go overlay contains 54 authored references to all 26 canonical operation forms; the Python overlay contains 30 authored references to 25 forms because the classic `nats-py` distribution does not expose a distinct `consumer.update` method. That difference remains an SDK-surface fact rather than duplicated or altered service meaning.

The Go generator resolves each `operationRef` into the same Condition kind, interface type, fixed operation fields, and required or optional binding contract defined by the service mapping. It rejects unknown references, stale service-mapping identity, missing required bindings, extra fields, and authored `conditionTemplate` blocks. The generated Go mapping retains both the canonical reference and a resolved template so the existing profiler can consume a self-contained mapping without learning a new contract. This is deliberate build-time compatibility, not a second service-semantic authority. Removing YAML aliases and retaining canonical references increased the generated file from 38,687 to 44,120 raw bytes, but gzip size increased by only 173 bytes, from 2,543 to 2,716; portability and traceability therefore cost little in the shipped static artifact.

The six Go and six Python fixtures are not source-equivalent applications and therefore should not be described as producing identical operation lists. They use different values and exercise different SDK methods. The valid cross-language equivalence claim is narrower and stronger: every referenced operation in both languages resolves through one service mapping, overlapping references resolve to the same Condition form, and each real profiler emits only extension-valid Conditions from its application's source-proven values.

## Current source-surface result

The deterministic audit scopes 186 exported functions and methods across Core NATS and the modern JetStream interfaces. It reports 86 mapped, 64 excluded, 36 deferred, and zero unclassified. The difference between 86 mapped operations and 87 mapping call records is intentional: `jetstream.New` produces inherited state but emits no condition of its own.

The 64 exclusions are predominantly connection lifecycle, local state, diagnostics, callback registration, cached information, or asynchronous bookkeeping that adds no adapter-actionable demand. The 36 deferred operations are not profile warnings. They are decisions that block a comprehensive semantic claim until extension and adapter review occurs.

The deferred groups are:

- create-or-update methods whose result depends on remote state while the extension requires one fixed action;
- service-wide discovery methods that do not prove the stream, consumer, or bucket coordinates required by current operation forms;
- consumer reset, pause, resume, and unpin behavior absent from the extension vocabulary;
- stream message mutation and inspection behavior absent from the extension vocabulary;
- key/value and object-store configuration updates and object-store sealing absent from the extension vocabulary;
- object-store links that may introduce a second resource dependency;
- the separate legacy JetStream API exposed through `Conn.JetStream`.

Those gaps should be reviewed with NATS maintainers and adapter authors. Some may justify new adapter-actionable operations, some may need a more expressive mapping construct, and some may remain safely excluded. We should not force them into existing actions merely to increase a coverage number.

## Application acceptance result

[`tools/verify_fixtures.py`](tools/verify_fixtures.py) creates an isolated Go workspace, stages the generated metadata into the pinned SDK source, compiles every fixture, runs the actual profiler with semantic Go package loading required, and compares each result with its reviewed YAML profile. Profile generation does not skip extension validation.

The focused fixtures prove Core NATS messaging, JetStream stream publishing, consumer state, key/value state, and object-store state independently. The comprehensive fixture emits two conditions and 30 operations. Its primary condition contains all 26 `(resource, action)` combinations defined by the extension, with application-provided stream, consumer, subject, and bucket values, plus separate consumer operations that exercise both service-level and stream-level producer paths. Its secondary condition contains only connection and `audit.created` publication operations from the separately assigned connection.

The comprehensive fixture specifically verifies the approved mixed-responsibility model: the extension defines that a stream creation operation may carry `name` and `subjects`; the mapping says those values come from `cfg.Name` and `cfg.Subjects`; the real `CreateStream` signature and `StreamConfig` type validate the binding; and unchanged application source supplies `ORDERS` and `orders.>`. The same profiler mechanism resolves consumer names and key/value or object-store buckets without any NATS field names in profiler code.

## Historical maintenance evidence

The expanded 87-record mapping's symbols and bindings validate without authored semantic changes against nats.go v1.51.0, v1.52.0, and v1.53.1. This supersedes the earlier result that covered only 20 calls and three state types.

The replay also found real maintenance work. `ResetConsumer` and `ResetConsumerToSequence` were absent in v1.51.0 and appeared in v1.52.0 on both `StreamConsumerManager` and `ConsumerManager`, adding four scoped public symbols. They required a maintainer-facing classification decision. The current decision defers all four forms because consumer reset behavior is not represented by the NATS extension. They required no mapping change, but they are exactly the kind of API semantic change that the extension-maintenance path must surface for review. v1.52.0 and v1.53.1 share the current 186-symbol classification with no further authored operation, binding, or policy change.

The historical sources received source compatibility checks, not separately packaged mappings with rewritten version and revision metadata and not full fixture profiling. [`results/release-replay.yaml`](results/release-replay.yaml) records that boundary.

## What remains unresolved

The current local-value analysis is intentionally shallow. It does not propagate configurations through aliases, helper returns, struct fields, containers, or arbitrary control flow. Explicit address taking invalidates a remembered value, but the profiler does not yet model every possible implicit or indirect mutation path. These boundaries need additional generic data-flow design and regression tests before the behavior can be called complete. They must not be addressed with NATS-specific field logic.

The NATS extension still needs the semantic review represented by the 36 deferred operations. The current profiles are valid against the current extension, but validity is not the same as full SDK coverage.

The annotation format is still too large to accept as the final SDK-author experience after removing embedded Condition templates and YAML anchors. The next ergonomics investigation should identify how much of the remaining 892-line binding and state input can be projected from Go source, reusable language-level rule forms, and concise maintainer overlays while keeping every SDK-specific choice visible and deterministic.

The pinned-release GitHub Actions workflow now runs the generator tests, verifies deterministic mapping output, rebuilds the source-surface classification, executes all six fixtures through the real profiler, and runs the profiler regression suite. It is not yet an upstream NATS repository integration or ongoing release watcher. The deterministic generator, source audit, package staging, and acceptance harness are the components from which that workflow can be built after maintainer review.

## Result and next decision

Accept the NATS experiment as evidence that one reviewed service authority can feed two independently shaped SDK languages without duplicating Condition semantics in their authoring overlays. Do not accept it as evidence that the current SDK-authoring syntax is sufficiently compact. The next independent SDK case should test whether the operation-reference and state/binding boundaries survive a different SDK architecture; separately, future Go authoring research should reduce the remaining mechanical structure using evidence from more than NATS before defining common shortcuts.
