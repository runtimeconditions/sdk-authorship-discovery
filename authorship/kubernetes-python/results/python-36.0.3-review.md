# Kubernetes Python 36.0.3 SDK surface review

**Classification: `investigation`**

The complete transformed generator input joins statically to both generated Python API surfaces and feeds the conforming SDK mapping bound to the immutable Kubernetes API extension release. This report remains the lower-level SDK-authorship inventory rather than the mapping review surface.

## Owner

- Repository: `https://github.com/kubernetes-client/python.git`
- Revision: `67e7d9abfc6fe6629fa650d9b0abf4c99ef8c39c`
- Distribution: `kubernetes==36.0.3`

## Exact inputs

- Retained authoritative snapshot SHA-256: `c316f6e232c666148076e82e20371ff656ffbb12e59d8953e6d94ec7685bc75c`
- Retained authoritative snapshot semantic SHA-256: `ca58855c8fe1774f8859e957ec94ebb41b016ea726e986f166460eefce488cfd`
- Transformed generator input SHA-256: `642b0eb32a68f326642aee70f3ff8530730616d2cc60b2994364ca199975bfb3`
- Transformed generator input semantic SHA-256: `6df0f8c041370f2bd133a3fe8dce763e8e89dbffa84ee81b45401d32203a58e8`
- Target authoritative inventory semantic SHA-256: `0ea1345e622231970d47bd80a0babc84a7425edf17596673e9112882b0b2a701`

## Generated surface

- Generator operations: 936
- Synchronous public methods: 936
- Asynchronous public methods: 936
- Authoritative endpoint joins: 908
- SDK-injected dynamic endpoint/method records: 28 (27 custom-resource records and 1 discovery record)
- Generator operation-ID renames: 903
- Reused generator operation IDs: 118 names across 338 endpoints
- Joins requiring normalized trailing-slash equivalence: 2
- Methods exposing a `watch` argument: 132
- Statically derived list-to-watch conditional projections: 129
- Source-verified handwritten condition delegations: 1

## Representative join

`kubernetes.client.api.core_v1_api.CoreV1Api.read_namespaced_config_map` and `kubernetes.aio.client.api.core_v1_api.CoreV1Api.read_namespaced_config_map` join through transformed operation `readNamespacedConfigMap` and `GET /api/v1/namespaces/{namespace}/configmaps/{name}` to authoritative operation `readCoreV1NamespacedConfigMap`.

## SDK-owned review surface

The 908 generated endpoint mappings and 1872 generated public symbols require no handwritten method table. The generator or adjacent build step can emit them from the retained processed model and generated source verification. Reused transformed operation IDs confirm that endpoint plus owning class must remain part of SDK identity.

The focused SDK-owned semantic surface contains 27 distinct custom-resource method records, 1 API-discovery method record, 1 source-verified handwritten condition delegation, and any future wrappers or aliases absent from the processed model. These records must not collapse into one operation with combinatorial verb, scope, or subresource choices: each public SDK method determines one fixed base verb, scope, and optional subresource, while the 3 list methods have one explicit source-proven `watch=true` override and only resource coordinates such as group, version, and plural resource bind from method arguments. `Watch.stream` contributes no standalone Kubernetes condition; it delegates to the mapped callable and activates only a conditional argument declared by that target. A shared generator rule may emit and validate the separate records, but it is not itself an SDK mapping operation. A record must not emit a concrete resource requirement when application source leaves required coordinates unresolved.

## Next gate

Review the single source-verified `Watch.stream` delegation annotation and its profiler behavior, then investigate whether `DynamicClient` and discovery-created `Resource` state can be represented without broad conditions or per-resource annotations.
