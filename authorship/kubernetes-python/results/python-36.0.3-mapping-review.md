# Kubernetes Python conforming mapping review

**Classification: `accepted`**

The verified Kubernetes Python 36.0.3 surface compiles into a mapping that targets one exact immutable Kubernetes API extension release.

## Artifact

- Distribution: `kubernetes==36.0.3`
- Mapping: `kubernetes.api`
- Mapping semantic SHA-256: `55d73f8b70575d753c115c6ed4c637796a91ba1050ed151792c051027025b212`
- Target extension: `https://runtimeconditions.io/extensions/kubernetes-api/0.1.0/runtimeconditions.extension.yaml`
- Target extension semantic SHA-256: `b051163962d807642703a6626f1f9297de6681fb5773182c50e3dbde1774d62e`
- Operation records: 936 (908 authoritative and 28 dynamic)
- Public sync/async symbols: 1873
- Conditional list-to-watch methods: 132
- Source-verified condition delegations: 1

## Representative typed-client join

`CoreV1Api.read_namespaced_config_map` references `readCoreV1NamespacedConfigMap`, which emits the accepted core/v1 namespaced ConfigMap `get` operation.

## Dynamic method contract

The mapping contains 28 separate dynamic endpoint/method records. For example, `CustomObjectsApi.create_namespaced_custom_object` fixes `create` and `namespaced`; only API group, API version, and plural resource bind from that method's required arguments. No operation record contains a list of possible verbs, scopes, or subresources.

## SDK-author review surface

Generated typed-client records require no handwritten method table. Maintainers review the generator integration, the separate dynamic binding rule, one source-verified `Watch.stream` delegation annotation, future handwritten wrappers, and the concise release difference. The generated mapping YAML is not a line-by-line review surface.

## Scope boundary

This mapping conforms to the extension for the complete generated typed-client surface and the handwritten `Watch.stream` delegation. The wrapper contributes no generic Kubernetes condition: a profiler must resolve its callable argument, inherit that target's mapped condition, forward application arguments, and activate only a conditional argument declared by the target. `DynamicClient`, discovery-created `Resource` state, and other non-generated package behavior remain outside this mapping.
