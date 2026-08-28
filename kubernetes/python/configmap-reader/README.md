# Kubernetes ConfigMap reader

This project is the baseline Kubernetes Python case. It loads the ordinary in-cluster or local kubeconfig configuration, constructs the generated `CoreV1Api` client, and calls `read_namespaced_config_map`.

The expected profiler conclusion is that the workload uses the Kubernetes API to get a namespaced core/v1 ConfigMap. Client construction, kubeconfig loading, a literal namespace, and a literal object name must not independently create additional Runtime Conditions or configuration conventions.

The candidate extension representation is intentionally under review in `extensions/kubernetes-api`. The application fixture does not depend on that representation and must not be rewritten to accommodate it.

Install the project from the SDK corpus root:

```sh
python -m pip install -e ./kubernetes/python/configmap-reader
```

Run against the Kubernetes context selected by the ordinary Python client configuration:

```sh
kubernetes-configmap-read application-settings --namespace default
```

Test without Kubernetes access:

```sh
python -m unittest discover -s tests
```
