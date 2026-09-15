# NATS Go SDK authorship experiment

## Status

**Working cross-language service-authority and real-profiler acceptance proof; ready for semantic and SDK-maintainer-experience review, not public release.**

This experiment tests a primarily handwritten SDK against the official `github.com/nats-io/nats.go` module. It covers Core NATS and the modern JetStream publisher, stream, consumer, key/value, and object-store interfaces through six unchanged Go applications under [`../../nats/go`](../../nats/go).

## Language-neutral service authority

The language-neutral 26-operation Service Operations Inventory lives in the separate [`runtimeconditions/service-operations-inventories`](https://github.com/runtimeconditions/service-operations-inventories) repository because this workflow has no adequate authoritative Smithy, OpenAPI, or equivalent operation model to project. The current NATS compiler combines that neutral source with [`service-operations-semantic-bridge.yaml`](../../../extensions/nats-service/model/service-operations-semantic-bridge.yaml) to produce [`nats-service-mapping.yaml`](../../../extensions/nats-service/model/generated/nats-service-mapping.yaml). Stable names such as `subject.publish`, `stream.create`, and `consumer.consume` are shared by every NATS SDK language. The bridge is an experimental service-level supplement, not an SDK-author artifact, and must be removed if the same projection can be derived from an adequate inventory and extension definition.

The Go annotation now references those canonical operations and records service-mapping semantic digest `791de4f22212d2c6e61952a154ca6c1bd1904c6c430c766cb27680a8aeb01cb7`. The generator resolves each reference against the service mapping, validates its required and optional bindings, and expands it into the self-contained Condition template consumed by the existing Go profiler. The generated repetition is build output rather than SDK-maintainer input; this conversion required no profiler change and produced the same reviewed application profiles.

## SDK author input

[`annotations/go.yaml`](annotations/go.yaml) is the reviewed SDK-integration input for this release. It has 35 individually described calls and 20 call groups covering another 52 methods. The generator expands those rules into 87 exact call records: 86 adapter-actionable public operations and one state-only bridge from the Core NATS connection to the JetStream API. Six generic state types preserve resource coordinates and the source-proven identity of the NATS connection on which later calls depend.

This is materially larger than the original 20-call proof and must not be described as a small maintainer input. The anchor-free annotation file is currently 892 lines. It contains 54 canonical operation references covering all 26 NATS operation forms; call-group expansion produces 86 mapped call records. Removing authored Condition templates and YAML anchors reduced the file by only 71 lines because repeated SDK binding and state structure remains. This experiment proves the authority boundary, but it also demonstrates that operation references alone do not make the present YAML ergonomics acceptable for adoption.

[`maintenance/surface-policy.yaml`](maintenance/surface-policy.yaml) scopes the public SDK surface and records why a public symbol is mapped, excluded from Runtime Conditions, or deferred for semantic review. The generated [`results/surface-coverage.yaml`](results/surface-coverage.yaml) reports 186 scoped public symbols: 86 mapped, 64 excluded because they add no adapter-actionable demand, 36 deferred, and zero unclassified. These classifications are maintenance evidence only. They are not shipped in the SDK mapping or emitted in an application profile.

SDK maintainers should not be expected to write or maintain the project-specific generator, source parser, staging tool, or fixture harness found under [`tools`](tools). Those are prototypes for shared Runtime Conditions authoring tooling. A participating SDK maintainer's intended responsibility is to review the compact semantic and binding input, classify newly introduced public operations, enable the shared release check, and ship the generated static metadata. The current experiment lets us measure how far the prototype remains from that intended experience.

No SDK public method changes, annotations in Go source, generated Go code, runtime initialization, application dependency, or Runtime Conditions runtime library are required.

## Generic binding contract

The extension and its language-neutral service mapping own the condition kind, interface, operation forms, validation rules, stable operation names, and adapter-actionable distinctions. The SDK mapping selects an exact public symbol and names the parameter or typed struct field that supplies each extension field. The Go function signature and type declarations validate those names. Ordinary application source supplies the concrete value.

For example, the NATS mapping says that a stream operation's `name` comes from the `Name` field of the method's `cfg` parameter. The profiler contains no knowledge of `Name`, `StreamConfig`, buckets, subjects, or NATS. It follows a direct local initializer such as `streamConfig := jetstream.StreamConfig{Name: "ORDERS"}` or an initialized local `var` declaration and emits only the values that remain statically proven. A later reassignment or field mutation invalidates that local value, and an unresolved value emits no widened condition.

The mapping also declares generic producer state and dependency identity. `nats.Connect` starts a new dependency identity, `jetstream.New(connection)` inherits it from its argument, and resource-producing calls inherit it from their receiver. Conditions merge only when the extension, condition shape, and source-proven dependency identity match. Two separately assigned connections therefore remain two Runtime Conditions.

The shipped generated mapping retains both the canonical `operationRef` and its resolved `conditionTemplate`. The reference records the service mapping join, while the template preserves compatibility with the current Go profiler's self-contained mapping contract. The build rejects unknown operation references, stale service-mapping coordinates, missing required bindings, fields absent from the service operation, and any attempt to author a Condition template directly in the Go overlay.

## Local packaging

[`tools/stage_module.py`](tools/stage_module.py) copies the generated mapping into `runtimeconditions/mappings/nats-service.yaml` in a local NATS module source tree and writes `runtimeconditions/index.yaml` with the exact module version and mapping digest. Go modules include these ordinary non-Go files without a package manifest or registry publication change. The fixtures use a temporary Go workspace replacement that points the normal `github.com/nats-io/nats.go v1.53.1` dependency at this staged source tree.

The files shipped by an SDK release are the generated mapping and distribution index. The coverage report, fixture profiles, and experiment tools are Runtime Conditions research and verification artifacts, not additional SDK package contents.

## Reproduce

Generate the mapping from the SDK repository root:

```sh
.venv/bin/python authorship/nats-go/tools/generate_mapping.py --annotations authorship/nats-go/annotations/go.yaml --service-mapping ../extensions/nats-service/model/generated/nats-service-mapping.yaml --extension ../extensions/nats-service/releases/0.1.0/runtimeconditions.extension.yaml --output authorship/nats-go/mappings/runtimeconditions.sdk-mapping.yaml
```

Validate the mapping and classify the public surface against a released NATS source tree:

```sh
cd authorship/nats-go/tools
go run . --sdk-root /absolute/path/to/nats.go --mapping ../mappings/runtimeconditions.sdk-mapping.yaml --coverage-policy ../maintenance/surface-policy.yaml --coverage-output ../results/surface-coverage.yaml
```

Build the real Go profiler, then run all six applications through it and compare their schema-valid results with the reviewed profiles:

```sh
.venv/bin/python authorship/nats-go/tools/verify_fixtures.py --profiler /absolute/path/to/go-rc-profiler --sdk-source /absolute/path/to/nats.go --mapping authorship/nats-go/mappings/runtimeconditions.sdk-mapping.yaml --fixtures-root nats/go --extensions-root ../extensions --expected-root authorship/nats-go/results/profiles
```

[`REVIEW.md`](REVIEW.md) is the cohesive review document for the contract, author burden, acceptance evidence, historical replay, and unresolved decisions.

[`../../.github/workflows/nats-go.yml`](../../.github/workflows/nats-go.yml) reproduces the pinned-release proof on relevant changes and manual runs: service-mapping compilation tests, deterministic mapping generation, public-surface classification, all six real-profiler fixtures, and the complete Go profiler regression suite. It is not yet an ongoing NATS release watcher.
