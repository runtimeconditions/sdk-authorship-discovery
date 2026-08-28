# Kubernetes SDK investigation

This directory contains unchanged application projects used to investigate the official Kubernetes client libraries. The first project uses the generated Python client because the Python profiler already exists and the client provides a direct comparison with the model-generated AWS Python work.

The applications contain no Runtime Conditions declarations or mapping metadata. Kubernetes extension semantics and SDK-owned mappings are developed separately so the application-adopter experience remains the primary acceptance gate.

## Projects

| Project | SDK pattern | Static expectation | Mapping question |
| --- | --- | --- | --- |
| `python/configmap-reader` | `CoreV1Api.read_namespaced_config_map` | Resolvable | Can an OpenAPI-generated client method prove Kubernetes API access for one namespaced resource operation without assuming a cluster, endpoint, credentials, namespace value, or configuration convention? |
