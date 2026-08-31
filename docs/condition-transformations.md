# Delegated condition transformations

## Purpose

An SDK wrapper may preserve an underlying external dependency while modifying the operation that the application performs through it. The wrapper must not declare a broad standalone Runtime Condition when the actual resource or endpoint is determined by a delegated SDK call.

Kubernetes Python `Watch.stream` is the first accepted example. It receives another SDK method as `func`, forwards the remaining positional and keyword arguments, selects either the delegated method's `watch` or `follow` control argument, sets that argument to `true`, and invokes the method. For a mapped list method, this changes the Kubernetes operation from `list` to `watch` while retaining the API group, API version, resource, and scope supplied by the delegated method. For `read_namespaced_pod_log`, no mapped conditional matches `follow`, so the underlying `get pods/log` operation is preserved.

## Mapping contract

The wrapper record is a delegation, not an operation:

```yaml
python:
  conditionDelegations:
  - id: watch-stream
    symbols:
    - module: kubernetes.watch.watch
      class: Watch
      method: stream
    delegate:
      callableArgument:
        position: 0
        keyword: func
      forwardedArguments:
        positional:
          fromPosition: 1
        keywords: true
      activateTargetConditionals:
      - argument:
          keyword: watch
        equals: true
      - argument:
          keyword: follow
        equals: true
```

`callableArgument` identifies the application expression containing the delegated SDK method. `forwardedArguments` describes how the wrapper presents application arguments to that method. `activateTargetConditionals` describes source-proven argument effects that may activate condition changes already declared by the delegated method mapping.

The wrapper does not contain `operationRef`, a condition template, Kubernetes resource coordinates, or a generic Kubernetes condition. The delegated method remains the authority for those semantics.

## Profiler consumer contract

A conforming profiler consumer performs these steps without importing or executing the application or SDK:

1. Discover the version-aligned SDK mapping from the installed distribution metadata and verify the index, file digest, mapping semantic digest, distribution version, and exact extension coordinates.
2. Resolve the wrapper call to a `conditionDelegation` symbol.
3. Resolve the configured callable argument to one mapped SDK method.
4. Construct the delegated call view by forwarding the declared arguments and applying the declared target-conditional activations.
5. Resolve the delegated method's ordinary operation or condition template.
6. Apply only a matching delegated-method conditional transformation.
7. Validate the resulting condition against the exact extension release before emitting it.

If the wrapper, callable argument, target method, required dynamic coordinate, conditional value, mapping digest, or extension release cannot be resolved exactly, the profiler emits no inferred SDK condition or fails closed for invalid installed metadata. It never emits a broad condition merely because the wrapper symbol is present.

## Authoring and maintenance boundary

The Kubernetes SDK authoring input is one wrapper annotation, not one annotation per possible delegated method. The deterministic projection verifies the wrapper symbol, callable argument, `*args` and `**kwargs` forwarding, source-selected target argument names, and source assignment of `true`. Generated typed-method metadata continues to own the resource and operation-specific conditional behavior.

An ordinary generated endpoint addition does not change the wrapper annotation. Human review is required when the wrapper signature, forwarding behavior, target-argument selection, or semantic effect changes. The generated mapping YAML remains machine output and is not a line-by-line maintainer review surface.

## Current scope

This contract proves one higher-order callable delegation in Python. It is not yet a universal wrapper schema. The separate [`stateful-resource-flows.md`](stateful-resource-flows.md) result covers the first producer/object-state/method pattern without pretending it is a callable delegation. OpenTelemetry exporters, OpenFeature providers, and other SDKs may reveal construction-time, configuration, or multi-target transformations that require additional focused vocabulary. Those additions must preserve the same rule: modifiers compose with conditions proven by their delegate and do not invent a generic dependency when the delegate is unresolved.
