# Kubernetes Python SDK authorship investigation

## Status

**Accepted generated typed-client, `Watch.stream`, and DynamicClient base-resource mapping with local profiler, packaging, and historical replay proof.**

This project measures what the official Kubernetes Python maintainers would generate, annotate, package, and maintain. It consumes the exact source retained by Python client 36.0.3, the language-neutral authoritative Kubernetes operation inventory, and the immutable Kubernetes API extension release.

## Current result

[`results/python-36.0.3-mapping-review.md`](results/python-36.0.3-mapping-review.md) is the conforming mapping review, [`results/packaging-review.md`](results/packaging-review.md) records the local wheel and real-profiler proof, and the accepted profiles cover the unchanged generated reader, wrapper watcher, dynamic ConfigMap lifecycle, dynamic Resource watcher, and deliberately unresolved CRD reader. [`results/release-replay.md`](results/release-replay.md) records a retrospective compatibility replay plus the authored tooling repair discovered during the investigation. [`maintenance/replay-observations.yaml`](maintenance/replay-observations.yaml) is the non-generated, reviewable maintenance record used to prevent regenerated evidence from erasing that work. [`results/python-36.0.3-review.md`](results/python-36.0.3-review.md) remains the lower-level generated-surface review. The generated surface and mapping YAML files are deterministic machine outputs and are not intended for line-by-line review.

The projection statically parses generated and handwritten source without importing or executing the SDK. It verifies every transformed generator endpoint against every generated flavor present in the release, joins every non-dynamic endpoint back to authoritative Kubernetes semantics, preserves argument bindings for generator-injected dynamic paths, identifies direct list-to-watch conditional behavior, validates the single authored `Watch.stream` delegation annotation, and verifies one DynamicClient producer/state/method flow against the actual client, discoverer, and Resource proxy implementations.

## Reproduce locally

Install the authoring-only dependency and provide an immutable Kubernetes Python v36.0.3 source checkout:

```sh
python -m pip install -r authorship/kubernetes-python/requirements.txt
python authorship/kubernetes-python/tools/project_surface.py \
  --source-root /absolute/path/to/kubernetes-client-python-v36.0.3 \
  --authoritative-inventory ../extensions/kubernetes-api/model/generated/kubernetes-v1.36-operation-inventory.yaml \
  --repository https://github.com/kubernetes-client/python.git \
  --revision 67e7d9abfc6fe6629fa650d9b0abf4c99ef8c39c \
  --version 36.0.3 \
  --sdk-annotations authorship/kubernetes-python/annotations/python.yaml \
  --surface-output authorship/kubernetes-python/results/python-36.0.3-surface.yaml \
  --review-output authorship/kubernetes-python/results/python-36.0.3-review.md

python authorship/kubernetes-python/tools/generate_mapping.py \
  --surface authorship/kubernetes-python/results/python-36.0.3-surface.yaml \
  --service-mapping ../extensions/kubernetes-api/model/generated/kubernetes-service-mapping.yaml \
  --extension ../extensions/kubernetes-api/releases/0.1.0/runtimeconditions.extension.yaml \
  --mapping-output authorship/kubernetes-python/mappings/runtimeconditions.sdk-mapping.yaml \
  --review-output authorship/kubernetes-python/results/python-36.0.3-mapping-review.md
```

## SDK-author burden demonstrated so far

The generated typed-client surface requires no handwritten operation table. Its 27 distinct custom-resource method records and one API-discovery method record are generated from route and signature evidence; a shared parameter-binding rule emits the separate records without collapsing them into one operation with combinatorial choices. The handwritten SDK surface adds one concise delegation covering `Watch.stream` and one DynamicClient flow covering seven public methods and nine fixed branches. The extension generates the 95-entry built-in selector catalog, and the SDK generator emits eight distinct state-bound operation templates. The ordinary wheel needs one static package-data declaration and no Runtime Conditions runtime dependency.

[`docs/sdk-author-workflow.md`](docs/sdk-author-workflow.md) states the exact maintainer steps and recurring work. [`../../docs/condition-transformations.md`](../../docs/condition-transformations.md) defines the delegated-condition contract, and [`../../docs/stateful-resource-flows.md`](../../docs/stateful-resource-flows.md) defines the new producer/state/method result and its generalization boundary. Unmodeled CRDs, dynamic subresources, ResourceList fan-out, constructor-only discovery traffic, and future wrappers absent from the retained models remain explicit boundaries rather than implied coverage.
