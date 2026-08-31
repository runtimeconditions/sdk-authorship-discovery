# Kubernetes DynamicClient CRD reader

This unchanged application follows the official Kubernetes Python custom-resource example and selects `apps.example.com/v1` kind `IngressRoute` through live API discovery.

The application proves group, version, and kind, but not the CRD's plural resource name or scope. Those facts are supplied by the target cluster's discovery response rather than the Kubernetes built-in OpenAPI model. A static profiler must therefore emit no concrete Kubernetes condition for this application unless another application source proves that missing metadata.

Run the tests without Kubernetes access with `python -m unittest discover -s tests`.
