# Kubernetes pod watcher

This application uses the official Kubernetes Python client's handwritten `Watch.stream` wrapper with a generated typed-client method. It contains no Runtime Conditions declarations or mapping files.

The expected profile contains one namespaced core/v1 Pod `watch` operation. The wrapper receives `CoreV1Api.list_namespaced_pod` as a callable, forwards the application arguments, and activates the delegated method's source-proven list-to-watch conditional behavior.
