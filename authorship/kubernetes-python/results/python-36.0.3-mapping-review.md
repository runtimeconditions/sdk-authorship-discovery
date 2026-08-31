# Kubernetes Python conforming mapping review

**Classification: `accepted`**

The verified Kubernetes Python 36.0.3 surface compiles into a mapping that targets one exact immutable Kubernetes API extension release.

## Artifact

- Distribution: `kubernetes==36.0.3`
- Mapping: `kubernetes.api`
- Mapping semantic SHA-256: `4d2cde51a3142f69466748d43aa2614f5ef5657591305726637f1fdab3d0e041`
- Target extension: `https://runtimeconditions.io/extensions/kubernetes-api/0.1.0/runtimeconditions.extension.yaml`
- Target extension semantic SHA-256: `b051163962d807642703a6626f1f9297de6681fb5773182c50e3dbde1774d62e`
- Operation records: 944 (908 authoritative, 28 generated dynamic, and 8 stateful templates)
- Mapped public symbols: 1875
- Conditional list-to-watch methods: 132
- Source-verified condition delegations: 1
- Source-verified stateful resource flows: 1
- Generated built-in discovery selectors: 95

## Representative typed-client join

`CoreV1Api.read_namespaced_config_map` references `readCoreV1NamespacedConfigMap`, which emits the accepted core/v1 namespaced ConfigMap `get` operation.

## Dynamic method contract

The mapping contains 28 separate generated dynamic endpoint/method records. For example, `CustomObjectsApi.create_namespaced_custom_object` fixes `create` and `namespaced`; only API group, API version, and plural resource bind from that method's required arguments. The handwritten DynamicClient flow contributes 8 distinct verb templates and 95 generated built-in resource selectors. It does not collapse the methods into one combinatorial operation.

## SDK-author review surface

Generated typed-client records require no handwritten method table. Maintainers review the generator integration, the separate generated-method binding rule, one source-verified `Watch.stream` delegation annotation, one stateful DynamicClient flow with seven methods, future handwritten wrappers, and the concise release difference. The generated mapping YAML and built-in resource selector catalog are not line-by-line review surfaces.

## Scope boundary

This mapping conforms to the extension for the complete generated typed-client surface, the handwritten `Watch.stream` delegation, and the source-verified DynamicClient base-resource flow. A profiler may resolve a discovery-created Resource only when statically resolved selectors match one generated built-in catalog entry. An unmodeled CRD remains unresolved because its plural name and scope exist only in live discovery state. Dynamic subresources, ResourceList fan-out, constructor-time discovery requests, and other non-generated package behavior remain explicit boundaries.
