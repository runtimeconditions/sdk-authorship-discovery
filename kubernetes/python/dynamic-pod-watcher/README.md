# Kubernetes DynamicClient Pod watcher

This unchanged application uses the public `Resource.watch` behavior documented by the official Kubernetes Python DynamicClient implementation.

The profiler should resolve the built-in core/v1 `Pod` selector and emit one namespaced `watch pods` operation. It should not additionally emit the internal `get` delegation used to implement streaming.

Run the tests without Kubernetes access with `python -m unittest discover -s tests`.
