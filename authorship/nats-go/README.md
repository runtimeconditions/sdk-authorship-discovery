# NATS Go SDK authorship experiment

## Status

**Working local SDK integration and real-profiler acceptance proof; ready for semantic and SDK-maintainer-experience review, not public release.**

This experiment tests a primarily handwritten SDK against the official `github.com/nats-io/nats.go` module. It covers Core NATS and the modern JetStream publisher, stream, consumer, key/value, and object-store interfaces through six unchanged Go applications under [`../../nats/go`](../../nats/go).

## SDK author input

[`annotations/go.yaml`](annotations/go.yaml) is the reviewed SDK-integration input for this release. It has 35 individually described calls and 20 call groups covering another 52 methods. The generator expands those rules into 87 exact call records: 86 adapter-actionable public operations and one state-only bridge from the Core NATS connection to the JetStream API. Six generic state types preserve resource coordinates and the source-proven identity of the NATS connection on which later calls depend.

This is materially larger than the original 20-call proof and must not be described as a small maintainer input. The annotation file is currently 963 lines. Much of that size is repeated extension templates and binding structure that a production authoring tool should reduce, but it remains part of the current human review surface. This experiment proves the contract and measures its burden; it does not establish that the present YAML ergonomics are acceptable for adoption.

[`maintenance/surface-policy.yaml`](maintenance/surface-policy.yaml) scopes the public SDK surface and records why a public symbol is mapped, excluded from Runtime Conditions, or deferred for semantic review. The generated [`results/surface-coverage.yaml`](results/surface-coverage.yaml) reports 186 scoped public symbols: 86 mapped, 64 excluded because they add no adapter-actionable demand, 36 deferred, and zero unclassified. These classifications are maintenance evidence only. They are not shipped in the SDK mapping or emitted in an application profile.

SDK maintainers should not be expected to write or maintain the project-specific generator, source parser, staging tool, or fixture harness found under [`tools`](tools). Those are prototypes for shared Runtime Conditions authoring tooling. A participating SDK maintainer's intended responsibility is to review the compact semantic and binding input, classify newly introduced public operations, enable the shared release check, and ship the generated static metadata. The current experiment lets us measure how far the prototype remains from that intended experience.

No SDK public method changes, annotations in Go source, generated Go code, runtime initialization, application dependency, or Runtime Conditions runtime library are required.

## Generic binding contract

The extension owns the condition kind, interface, operation forms, validation rules, and adapter-actionable distinctions. The SDK mapping selects an exact public symbol and names the parameter or typed struct field that supplies each extension field. The Go function signature and type declarations validate those names. Ordinary application source supplies the concrete value.

For example, the NATS mapping says that a stream operation's `name` comes from the `Name` field of the method's `cfg` parameter. The profiler contains no knowledge of `Name`, `StreamConfig`, buckets, subjects, or NATS. It follows a direct local initializer such as `streamConfig := jetstream.StreamConfig{Name: "ORDERS"}` or an initialized local `var` declaration and emits only the values that remain statically proven. A later reassignment or field mutation invalidates that local value, and an unresolved value emits no widened condition.

The mapping also declares generic producer state and dependency identity. `nats.Connect` starts a new dependency identity, `jetstream.New(connection)` inherits it from its argument, and resource-producing calls inherit it from their receiver. Conditions merge only when the extension, condition shape, and source-proven dependency identity match. Two separately assigned connections therefore remain two Runtime Conditions.

## Local packaging

[`tools/stage_module.py`](tools/stage_module.py) copies the generated mapping into `runtimeconditions/mappings/nats-service.yaml` in a local NATS module source tree and writes `runtimeconditions/index.yaml` with the exact module version and mapping digest. Go modules include these ordinary non-Go files without a package manifest or registry publication change. The fixtures use a temporary Go workspace replacement that points the normal `github.com/nats-io/nats.go v1.53.1` dependency at this staged source tree.

The files shipped by an SDK release are the generated mapping and distribution index. The coverage report, fixture profiles, and experiment tools are Runtime Conditions research and verification artifacts, not additional SDK package contents.

## Reproduce

Generate the mapping from the SDK repository root:

```sh
.venv/bin/python authorship/nats-go/tools/generate_mapping.py --annotations authorship/nats-go/annotations/go.yaml --extension ../extensions/nats-service/releases/0.1.0/runtimeconditions.extension.yaml --output authorship/nats-go/mappings/runtimeconditions.sdk-mapping.yaml
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
