# NATS Python SDK authorship experiment

This experiment maps the official `nats-py` 2.15.0 distribution through the shared NATS service mapping and validates the result with the real Python profiler. It is the second NATS SDK language explored and the first language mapping that directly consumes the shared service mapping while remaining faithful to a substantially different public API. The current service-mapping compiler also consumes an experimental semantic supplement; that is not an SDK-author responsibility and must be audited against the neutral inventory for direct derivation. The existing Go mapping is aligned but still embeds equivalent templates, so full two-language reuse is not yet proven until that mapping is converted to service-operation references.

## Result

The deterministic generator projects 3 typed configuration values, 2 factories, 22 individually described call rules, and 8 grouped rules into 42 call records covering 44 public methods. Six ordinary Python applications produce extension-valid reviewed profiles without Runtime Conditions code or configuration. The comprehensive fixture also proves that two separately constructed clients remain separate Runtime Conditions.

The profiler change is language-generic. It understands awaited values, mapped factories, typed SDK state, receiver-produced state, dependency identity, positional and keyword arguments, typed configuration fields, literal lists, alternative binding sources, and prior state fields. It contains no NATS symbol, field, operation, or resource name.

## What an SDK maintainer authors

[`annotations/python.yaml`](annotations/python.yaml) is the semantic integration input. An SDK maintainer reviews which public factory or method aligns to a service operation, which named source parameter supplies each required or optional extension field, what typed state a call returns, which values that state retains, and whether the returned state represents a new dependency or inherits an existing one. Repeated methods with identical meaning can use a call group.

[`maintenance/surface-policy.yaml`](maintenance/surface-policy.yaml) records the reasons that scoped public methods are excluded or deferred. A newly added public method fails the classification gate until it is mapped, excluded, or deferred. The generated report is maintenance evidence and is not shipped to application developers.

The current annotation is 501 lines. That is meaningfully smaller than the 941-line generated mapping, but it is still a material review surface and must not be presented as negligible SDK-maintainer work. The 22 individual rules contain SDK-specific choices that should remain visible; the 20 methods represented through groups avoid repeated choices. Future authoring work should reduce mechanical YAML without hiding those semantic decisions.

SDK maintainers are not expected to maintain the source parser, compiler, staging tool, profiler implementation, fixture harness, generated mapping, generated surface report, or generated application profiles by hand. Those are deterministic Runtime Conditions tooling responsibilities.

## What an SDK release ships

The staged distribution contains only `nats/runtimeconditions/index.yaml` and `nats/runtimeconditions/mappings/nats-service.yaml`. Both are static YAML files. The integration adds no imported module, initialization hook, runtime code, Runtime Conditions runtime dependency, or application-facing configuration.

The generated mapping includes the 26 operation definitions projected from the shared service mapping and records its exact semantic digest. SDK authors do not copy or maintain that operation table in their overlay. The SDK-specific rules refer to stable names such as `stream.create` and `key_value.read`.

## Generated evidence and trust boundary

The reviewed authoring inputs are `annotations/python.yaml` and `maintenance/surface-policy.yaml`. The SDK mapping, public-surface report, and fixture profiles are deterministic outputs. The profiles remain reviewed acceptance evidence, but they are never edited as a substitute for changing the authoring input or generator.

At build time, the generator requires the exact extension and generated service mapping. It rejects mismatched extension coordinates or semantic digests, copies the service mapping's operation records into the self-contained SDK mapping, and computes a new semantic digest over those operations plus the Python projection. At profiling time, discovery verifies the packaged mapping against the SDK's index and the profiler validates emitted Conditions against the exact extension release. The profiler does not fetch the service mapping: its provenance is established and reviewed at build time, while its generated operation records are sealed inside the independently integrity-checked SDK mapping. This avoids a third shipped file or an application-side network dependency.

## Deterministic workflow

1. Pin a released SDK source revision and the exact NATS extension and service-mapping digests.
2. Run [`tools/generate_mapping.py`](tools/generate_mapping.py). It verifies the distribution name, version, Git revision, referenced Python modules, classes, methods, dataclass fields, parameter names, service-operation fields, state producers, and state consumers before generating the mapping.
3. Run [`tools/project_surface.py`](tools/project_surface.py). It compares the scoped public source surface with the generated symbols and reviewed policy and rejects unclassified or conflicting methods.
4. Run [`tools/verify_fixtures.py`](tools/verify_fixtures.py). It copies the unmodified released distribution into a temporary directory, stages the two package files, syntax-checks each fixture, runs the real Python profiler, validates the generated profile against the exact extension, and compares it with reviewed YAML.
5. Review only changes to the compact overlay, classification policy, and application profiles. Generated-file diffs remain available as evidence but are not the primary human authoring surface.

## Reproduce

Generate the mapping:

```sh
.venv/bin/python authorship/nats-python/tools/generate_mapping.py --annotations authorship/nats-python/annotations/python.yaml --service-mapping ../extensions/nats-service/model/generated/nats-service-mapping.yaml --extension ../extensions/nats-service/releases/0.1.0/runtimeconditions.extension.yaml --source-root /absolute/path/to/nats.py/nats --output authorship/nats-python/mappings/runtimeconditions.sdk-mapping.yaml
```

Classify the public surface:

```sh
.venv/bin/python authorship/nats-python/tools/project_surface.py --source-root /absolute/path/to/nats.py/nats --mapping authorship/nats-python/mappings/runtimeconditions.sdk-mapping.yaml --policy authorship/nats-python/maintenance/surface-policy.yaml --output authorship/nats-python/results/surface-classification.yaml
```

Run the real-profiler acceptance suite:

```sh
.venv/bin/python authorship/nats-python/tools/verify_fixtures.py --profiler-root ../python-rc-profiler --sdk-source /absolute/path/to/nats.py/nats --mapping authorship/nats-python/mappings/runtimeconditions.sdk-mapping.yaml --fixtures-root nats/python --extensions-root ../extensions --expected-root authorship/nats-python/results/profiles
```

## Current semantic boundary

The source audit classifies 84 public methods: 44 mapped, 27 excluded because they add no adapter-actionable demand, 13 deferred for explicit semantic review, and zero unclassified. The separate classic `nats-py` distribution is the only package in scope; the newer independently versioned `nats-core`, `nats-jetstream`, and `nats-key-value` packages require their own mappings.

The classic SDK does not expose a distinct consumer-update method, so the complete fixture exercises 25 of the inventory's 26 operation forms. Deferred methods are not profile warnings or mapping-layer coverage declarations. They are authoring evidence for maintainers and extension stakeholders to decide whether the existing adapter-actionable vocabulary should expand.

The profiler intentionally resolves only source-proven values through the modeled Python object flow. An unresolved required binding omits that operation; an optional binding with no source value is omitted; and explicit `None` is treated as absent while valid falsey values remain available. The current dependency identity is source-call-site identity, which distinguishes separately constructed clients in ordinary application code but is not a claim to model the number of objects created dynamically at runtime. Arbitrary runtime data flow and delegation across separately mapped SDK packages remain future profiler contracts, not hidden NATS exceptions.

[`../../.github/workflows/nats-python.yml`](../../.github/workflows/nats-python.yml) reproduces the pinned-release proof on relevant repository changes and manual runs. It is intentionally not an ongoing release watcher yet. The next maintenance step is to observe a newer `nats-py` release, produce a focused source and profile diff, and measure which changes are mechanical versus which require SDK or extension review before generalizing that workflow.
