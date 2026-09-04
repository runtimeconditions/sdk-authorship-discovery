# NATS Go SDK authorship and profiler review

## Review status

**Classification: working real-profiler integration with an explicit and measurable SDK-author burden; not yet suitable to present as a finalized authoring experience.**

The official `nats.go` v1.53.1 source was staged locally with package-owned Runtime Conditions metadata. Six ordinary applications compiled against that staged module, and the real Go profiler produced extension-valid profiles for all six without Runtime Conditions declarations or configuration in application code. The comprehensive application exercises every operation form currently defined by the NATS extension and proves that two independently created connections remain separate Runtime Conditions.

This result proves more than the original NATS slice: exact named-parameter validation, typed struct-field binding, local configuration-value flow, state-only delegation, resource state propagation, dependency identity, safe condition grouping, deterministic surface classification, and fixture-level acceptance all work together. It also exposes authoring burden and extension gaps that should not be hidden by the successful profile output.

## The contract being tested

The extension supplies the adapter-actionable semantics. The SDK integration selects exact language symbols and binds extension fields to named parameters, typed fields, or prior producer state. The SDK's real function and type declarations validate those selections. The application supplies concrete values through ordinary source code. The profiler resolves only generic Go constructs and emits nothing when a required value or identity is not statically proven.

No layer invents another layer's facts. The extension does not name Go methods. The mapping does not define new extension actions. The profiler does not know NATS fields such as `Name`, `Bucket`, `Subjects`, or `Subject`. The application developer does not maintain SDK mappings.

The local-value addition is deliberately generic. A mapping can point to a named parameter and one typed field. If an application assigns a keyed struct literal directly with `:=` or an initialized local `var` declaration and passes that local to the mapped call, the profiler can resolve the selected field. Ordinary reassignment, field assignment, index assignment, or explicit address taking invalidates the remembered local value. Aliases, helper-function returns, values stored in structs or containers, control-flow joins that cannot be proven, and arbitrary data-flow are not resolved. This is a bounded language capability, not a NATS-specific `Name` lookup.

Producer state is also generic. A mapping may declare that a call creates a new dependency identity or inherits one from a receiver or state-bearing argument. Later calls can consume static fields from that producer state. The profiler groups compatible observations only when they target the same extension and condition shape and carry the same source-proven dependency identity. Calls without such proof stay separate.

## What an SDK maintainer would be asked to own

The current human-authored integration has 35 individual call descriptions and 20 grouped rules that expand to 52 additional methods. Together they generate 87 call records: 86 mapped public operations plus the state-only `jetstream.New` bridge. The input defines six state types. It is 963 lines of YAML.

That size is a warning, not a success metric. Call groups avoid individually repeating mechanically identical methods, but the present format still repeats templates and binding structures heavily. Before asking NATS maintainers to adopt this, shared authoring tooling should derive more boilerplate, present a concise review diff, and keep the maintainer focused on semantic decisions. We should evaluate the contract using this evidence without normalizing a 963-line hand-reviewed file as the expected end state.

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

The annotation format is too large to accept as the final SDK-author experience. The next ergonomics investigation should identify how much of the 963-line input can be projected from Go source, extension schemas, reusable rule forms, and concise maintainer overlays while keeping every semantic choice visible and deterministic.

The release workflow is not yet an upstream NATS repository integration or release watcher. The deterministic generator, source audit, package staging, and acceptance harness are the components from which that workflow can be built after maintainer review.

## Recommended review decision

Approve the generic profiler contract and the fixture evidence separately from the current authoring syntax. If the contract is sound, the next investigation should be the maintainer-facing input reduction, using the current 963-line annotation and the four-symbol consumer-reset release delta as measurable cases. In parallel, the deferred semantic groups should be presented to NATS maintainers and adapter authors as explicit questions rather than silently assigned to existing actions.
