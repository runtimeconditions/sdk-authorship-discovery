# Kubernetes Python local packaging review

## Outcome

The generated mapping was staged into an immutable Kubernetes Python v36.0.3 source archive, packaged in the normal `kubernetes` wheel, installed directly by path without a registry, automatically discovered through installed-distribution metadata, and verified against the exact Kubernetes API extension release without importing the SDK. The Python profiler resolved both the unchanged generated-client ConfigMap application and the unchanged `Watch.stream` Pod application while preserving its existing declarative-binding behavior.

## SDK source change

[`../patches/kubernetes-package-data.patch`](../patches/kubernetes-package-data.patch) adds one `package_data` declaration covering `runtimeconditions/index.yaml` and `runtimeconditions/mappings/*.yaml`. It does not change a generated client, public API, dependency declaration, or runtime code path.

## Installed artifacts

| Artifact | Uncompressed size |
| --- | ---: |
| `kubernetes/runtimeconditions/index.yaml` | 379 B |
| `kubernetes/runtimeconditions/mappings/kubernetes-api.yaml` | 864,683 B |

The baseline wheel was 2,342,280 bytes and the mapped wheel was 2,380,352 bytes, an increase of 38,072 bytes compressed. The installed index records mapping SHA-256 `2f92e4366799731236be323e2c4bf0e5a569c8c4d8dc7f12e4c0108330716559`.

The upstream `setup.py` build emits its existing setuptools deprecation warnings, and current setuptools also warns that the nested static-data directories resemble importable packages absent from the explicit package list. The files are included and installed correctly, but an upstream proposal should agree on a warning-free package-data location or explicit package declaration rather than normalize a noisy release build.

## Discovery and application proof

Installed discovery resolved `kubernetes.api` for `kubernetes==36.0.3`, verified the mapping file digest, semantic digest, distribution version, extension identifier, extension version, and independently recomputed extension semantic digest, and left `kubernetes` absent from `sys.modules`. The unchanged ConfigMap application resolved `CoreV1Api.read_namespaced_config_map` to one core/v1 namespaced ConfigMap `get` condition. The unchanged Pod watcher resolved `Watch.stream(CoreV1Api.list_namespaced_pod, ...)` to one core/v1 namespaced Pod `watch` condition. A direct list remained `list`, a wrapped Pod log operation remained `get pods/log`, client construction and configuration emitted nothing, and an unresolved delegated callable emitted nothing. A mixed application retained its existing declarative API and cache conditions while adding the mapped Kubernetes condition, proving that SDK extraction is additive rather than a replacement for the profiler's prior behavior.

## Boundary

This wheel contains a conforming mapping for all 936 generated typed-client endpoints, both generated flavors in v36.0.3, and one source-verified handwritten `Watch.stream` delegation. `DynamicClient`, discovery-resource delegation, and other non-generated package surfaces remain explicit SDK-authorship research items rather than implicit coverage.
