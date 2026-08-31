# Kubernetes SDK investigation

This directory contains unchanged application projects used to investigate the official Kubernetes client libraries. The first project uses the generated Python client because the Python profiler already exists and the client provides a direct comparison with the model-generated AWS Python work.

The applications contain no Runtime Conditions declarations or mapping metadata. Kubernetes extension semantics and SDK-owned mappings are developed separately so the application-adopter experience remains the primary acceptance gate.

## Projects

| Project | SDK pattern | Static expectation | Mapping question |
| --- | --- | --- | --- |
| `python/configmap-reader` | `CoreV1Api.read_namespaced_config_map` | Resolvable | Can an OpenAPI-generated client method prove Kubernetes API access for one namespaced resource operation without assuming a cluster, endpoint, credentials, namespace value, or configuration convention? |
| `python/pod-watcher` | `Watch.stream(CoreV1Api.list_namespaced_pod, ...)` | Resolvable through condition delegation | Can a handwritten wrapper transform a generated list condition into watch without declaring a broad wrapper condition? |
| `python/dynamic-configmap-lifecycle` | `DynamicClient.resources.get(api_version="v1", kind="ConfigMap")` followed by Resource methods | Resolvable through generated built-in discovery state | Can one source-verified stateful flow cover built-in dynamic resources without a handwritten per-resource table? |
| `python/dynamic-pod-watcher` | Discovery-created `Pod` Resource followed by `watch` | Resolvable through generated built-in discovery state | Can stateful method semantics preserve watch as one concrete operation rather than expose its internal delegation? |
| `python/dynamic-crd-reader` | Discovery-created custom `IngressRoute` Resource | Intentionally unresolved | Will the profiler refuse to invent the plural resource name or scope that only the live cluster proves? |
