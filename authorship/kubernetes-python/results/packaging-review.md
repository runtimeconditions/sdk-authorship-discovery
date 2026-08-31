# Kubernetes Python local packaging and profiler review

## Outcome

The generated mapping was staged into an immutable Kubernetes Python v36.0.3 source archive, packaged in the normal `kubernetes` wheel, installed directly by path without a registry, automatically discovered through installed-distribution metadata, and verified against the exact Kubernetes API extension release without importing the SDK. The real Python profiler resolved unchanged generated-client, `Watch.stream`, and DynamicClient applications while preserving its existing declarative-binding behavior.

## SDK source change

[`../patches/kubernetes-package-data.patch`](../patches/kubernetes-package-data.patch) adds one `package_data` declaration covering `runtimeconditions/index.yaml` and `runtimeconditions/mappings/*.yaml`. It does not change a generated client, public API, dependency declaration, or runtime code path.

## Installed artifacts

| Artifact | Uncompressed size |
| --- | ---: |
| `kubernetes/runtimeconditions/index.yaml` | 379 B |
| `kubernetes/runtimeconditions/mappings/kubernetes-api.yaml` | 948,012 B |

The baseline wheel was 2,342,346 bytes and the mapped wheel was 2,383,517 bytes, an increase of 41,171 bytes compressed. The installed index records mapping SHA-256 `ff7b9c48b7d50b1e70770405a8a66d3ca1ef0597e37235bff74152d2531e962d`; the mapping records semantic SHA-256 `4d2cde51a3142f69466748d43aa2614f5ef5657591305726637f1fdab3d0e041`.

The upstream `setup.py` build emits its existing setuptools deprecation warnings, and current setuptools also warns that the nested static-data directories resemble importable packages absent from the explicit package list. The files are included and installed correctly, but an upstream proposal should agree on a warning-free package-data location or explicit package declaration rather than normalize a noisy release build.

## Discovery and application proof

Installed discovery resolved `kubernetes.api` for `kubernetes==36.0.3`, verified the mapping file digest, semantic digest, distribution version, extension identifier, extension version, and independently recomputed extension semantic digest, and left `kubernetes` absent from `sys.modules`.

The five unchanged applications produced these results:

| Application | Result |
| --- | --- |
| Generated ConfigMap reader | One core/v1 namespaced ConfigMap `get` operation |
| `Watch.stream` Pod watcher | One core/v1 namespaced Pod `watch` operation |
| Dynamic ConfigMap lifecycle | Five separate core/v1 namespaced ConfigMap operations: `create`, `get`, `list`, `patch`, and `delete` |
| Dynamic Resource Pod watcher | One core/v1 namespaced Pod `watch` operation |
| Dynamic CRD reader | No inferred condition because source proves group/version/kind but not the plural resource name or scope supplied by live discovery |

A direct typed-client list remained `list`, a wrapped Pod log operation remained `get pods/log`, client construction and configuration emitted nothing, a DynamicClient selector using statically unresolved values emitted nothing, cluster-scoped Node access resolved `cluster`, and a namespaced collection call without a namespace resolved `all_namespaces`. A mixed application retained its existing declarative API and cache conditions while adding a mapped Kubernetes condition, proving that SDK extraction is additive rather than a replacement for the profiler's prior behavior.

## SDK-author review surface

The wheel contains 944 operation records: 908 authoritative generated endpoints, 28 separately generated dynamic endpoints, and 8 state-bound DynamicClient verb templates. It also contains 95 built-in discovery selectors generated from the extension's authoritative service inventory. Maintainers are not expected to author or inspect those records or selectors line by line.

The SDK-owned semantic input is one source-verified `Watch.stream` delegation and one source-verified DynamicClient flow covering its constructor aliases, `resources.get` producer chain, three selector inputs, seven public methods, and nine fixed operation branches. The package change remains the single static-data declaration and there is no Runtime Conditions runtime dependency.

## Boundary

This proof covers all 936 generated typed-client endpoints, both generated flavors in v36.0.3, `Watch.stream`, and the base-resource methods of a discovery-created DynamicClient `Resource` when literal selectors match one authoritative built-in catalog entry. It deliberately does not infer unmodeled CRDs, dynamic subresources, ResourceList fan-out, or conditions from constructing a DynamicClient alone. Constructor-time discovery traffic is an internal prerequisite of this client, but construction without a statically resolved resource operation is not treated as proof of an application resource demand.
