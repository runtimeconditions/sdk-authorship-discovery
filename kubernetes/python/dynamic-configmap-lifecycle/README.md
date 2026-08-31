# Kubernetes DynamicClient ConfigMap lifecycle

This unchanged application follows the official Kubernetes Python DynamicClient example: it selects the built-in core/v1 `ConfigMap` resource through API discovery and then creates, gets, lists, patches, and deletes ConfigMaps.

The application contains no Runtime Conditions declarations. The profiler may resolve the discovery-created object because the extension's authoritative built-in catalog maps core/v1 `ConfigMap` to the plural `configmaps` resource and namespaced scope.

Run the tests without Kubernetes access with `python -m unittest discover -s tests`.
