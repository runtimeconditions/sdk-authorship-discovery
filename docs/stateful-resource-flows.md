# Stateful SDK resource flows

## Purpose

Some SDKs do not expose a fixed client method for every external operation. They first produce an object whose state identifies a resource, then route later method calls through that object. Kubernetes Python `DynamicClient.resources.get(...)` is the first accepted example: live discovery creates a `Resource`, and `Resource.get`, `create`, `delete`, `replace`, `patch`, `server_side_apply`, and `watch` delegate through `DynamicClient` using the resource's group, version, plural name, and scope.

A mapping must preserve that two-stage data flow. Treating `Resource` as one operation would create the exact combinatorial design this investigation rejected. Treating every DynamicClient construction as a Kubernetes demand would create false positives when no resource operation is statically proven.

## Accepted Kubernetes shape

The SDK-authored flow identifies four things:

1. Constructor symbols that produce a DynamicClient value.
2. The member path `resources.get` that produces resource state.
3. The statically resolved selector arguments `api_version`, optional `group`, and `kind` used to choose that state.
4. Seven public Resource methods and nine fixed branches that each select one operation template.

The extension automation independently generates a catalog of 95 unambiguous built-in group/version/kind selectors from the authoritative Kubernetes inventory. Each catalog entry records the plural resource name, whether the resource is namespaced, and the exact verbs and scopes present in the extension vocabulary. The SDK mapping generator joins the one authored flow to that catalog and emits eight distinct templates: `create`, `delete`, `deletecollection`, `get`, `list`, `patch`, `update`, and `watch`.

The mapping declares scope resolution as data. For a namespaced collection, a meaningfully provided namespace argument produces `namespaced` and an omitted or statically empty value produces `all_namespaces`; a cluster-scoped resource produces `cluster`. The profiler evaluates these rules but contains no Kubernetes-specific scope policy.

## Resolution sequence

For this application source:

```python
resource = dynamic_client.resources.get(api_version="v1", kind="ConfigMap")
resource.get(name="settings", namespace="default")
resource.get(namespace="default")
```

the profiler first resolves the literal selector to one generated ConfigMap state record. It then resolves the first call to the fixed `get` template because `name` is present and the second call to the fixed `list` template because `name` is absent. The result is two ordinary extension-valid operations, not one operation with multiple parameter combinations.

Resolution fails closed. A statically unresolved selector, an ambiguous selector, an unsupported verb/scope pair, an invalid method branch, or a selector absent from the generated catalog emits no inferred SDK condition. For example, `Resource.delete` selects `deletecollection` only when a label or field selector is provided; a call with neither name nor selector is invalid SDK usage and emits nothing. A custom resource definition is not inferred from group/version/kind alone because its plural resource name and scope exist only in live discovery state.

## SDK-author burden

The Kubernetes maintainer review surface is one flow with two constructor aliases, one two-member producer path, three selector bindings, three implementation locations used for source verification, seven public methods, and nine fixed operation branches. There is no handwritten built-in resource list and no per-resource method table. The 95 selectors, 8 templates, and complete YAML mapping are deterministic outputs.

For each release, automation re-verifies the producer and Resource proxy implementations against pinned source, regenerates the selector catalog from extension semantics, rebuilds the mapping and wheel, and runs unchanged applications. Source drift becomes a focused validation failure. The current integration processed v36.0.0 through v36.0.3 without changing this flow or its operation branches.

## Generalization boundary

This result establishes a reusable data-flow pattern: a mapped producer can create statically known state, and later mapped methods can select fixed operations from that state. It does not establish a universal state schema for all SDKs. The current selector fields, capability catalog, branch rules, and scope values are Kubernetes-specific and belong in its extension and SDK mapping, not in application code or hard-coded profiler policy.

Future cohort cases may reuse the producer/state/method shape, but they must not be forced into Kubernetes resource vocabulary. A common contract should be extracted only after another independent SDK family demonstrates the same mechanics.
