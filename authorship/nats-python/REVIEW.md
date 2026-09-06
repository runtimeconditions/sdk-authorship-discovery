# NATS Python SDK authorship review

## Status

**Working real-profiler integration. The generic Python SDK-state contract was approved, implemented additively, and regression-tested against the existing AWS and Kubernetes integrations.**

The pinned `nats-py` source now generates a deterministic mapping that consumes the shared NATS service authority. Six ordinary applications produce extension-valid reviewed profiles through the real Python profiler, required dynamic values remain conservatively unreported, and two independently constructed NATS clients remain two Runtime Conditions. This is a successful implementation experiment, not yet a claim that the 501-line authoring overlay is the final SDK-maintainer experience.

## Experiment boundary

This experiment targets the official `nats-py` 2.15.0 distribution from [`nats-io/nats.py`](https://github.com/nats-io/nats.py) at tag `v2.15.0` and commit `24626a43631a21af2e35261cf0a8ec615fd35c78`. It maps Python SDK behavior through the generated NATS service mapping to the immutable NATS extension release. It does not change NATS service semantics merely to accommodate Python API design.

The same repository and release tag now contain separately packaged `nats-core`, `nats-jetstream`, and `nats-key-value` projects. Those are independent SDK distributions with their own versions and public surfaces. They are deliberately excluded from this first lane rather than being folded into `nats-py` metadata.

## Shared authority

The service-level authority is the neutral inventory in the separate [`runtimeconditions/service-operations-inventories`](https://github.com/runtimeconditions/service-operations-inventories) repository. The extension-owned [`service-operations-semantic-bridge.yaml`](../../../extensions/nats-service/model/service-operations-semantic-bridge.yaml) translates it into the generated [`nats-service-mapping.yaml`](../../../extensions/nats-service/model/generated/nats-service-mapping.yaml), which supplies the 26 canonical operation definitions and exact extension coordinates. The Python mapping must reference those operations and record service-mapping digest `791de4f22212d2c6e61952a154ca6c1bd1904c6c430c766cb27680a8aeb01cb7`; it must not copy the operation table into Python authoring input.

## Source-proven Python object flow

The ordinary top-level API is `client = await nats.connect(...)`. That function constructs `nats.aio.client.Client`, calls `Client.connect`, and returns the connected client. Users may alternatively instantiate the exported `nats.NATS` alias or `Client` directly and call `connect` themselves.

Core `Client` methods map directly to the shared operations: `connect` to `connection.connect`, `publish` to `subject.publish`, `subscribe` to `subject.subscribe`, and `request` to `subject.request`. `Client.jetstream()` and `Client.jsm()` do not add Conditions; they return JetStream contexts that inherit the connection dependency identity.

`JetStreamManager` and `JetStreamContext` expose stream and consumer operations. Direct cases such as `stream_info`, `delete_stream`, `consumer_info`, `delete_consumer`, `publish`, and `publish_async` have ordinary literal argument bindings. Creation and update methods also accept typed configuration objects or `**params`, so complete detection must resolve the API-declared configuration fields instead of coding names such as `name`, `subjects`, or `durable_name` into NATS-specific profiler logic.

`JetStreamContext.key_value(bucket)` and `object_store(bucket)` return objects whose later methods do not repeat the bucket. The SDK stores the supplied bucket on those objects. `create_key_value` and `create_object_store` likewise return bucket-bound objects. Read, write, inspect, and watch calls therefore require generic producer-to-returned-object state propagation.

## Inventory alignment

The existing inventory cleanly supports the following Python behavior without changing extension semantics:

| Python surface | Inventory operations |
| --- | --- |
| Connection and Core NATS | `connection.connect`, `subject.publish`, `subject.subscribe`, `subject.request` |
| JetStream stream lifecycle and publishing | `stream.create`, `stream.update`, `stream.delete`, `stream.inspect`, `stream.publish` |
| JetStream consumer lifecycle and consumption | `consumer.create`, `consumer.delete`, `consumer.inspect`, `consumer.consume` |
| Key/value manager and bucket objects | `key_value.create`, `key_value.delete`, `key_value.inspect`, `key_value.read`, `key_value.write`, `key_value.watch` |
| Object-store manager and bucket objects | `object_store.create`, `object_store.delete`, `object_store.inspect`, `object_store.read`, `object_store.write`, `object_store.watch` |

The classic Python SDK does not expose a distinct public consumer-update method matching `consumer.update`. This is an SDK-surface difference, not a reason to delete the canonical service operation used by other NATS SDKs.

Several public methods require semantic review rather than an automatic nearest-operation guess. `purge_stream`, stream listing, raw stream message access and deletion, consumer pause and resume, object-store sealing, and account inspection do not have exact current inventory forms. `JetStreamContext.subscribe` and `pull_subscribe` may inspect, create, bind, and consume depending on arguments and external server state. Because false positives are more damaging than incomplete detection, these methods remain deferred until the inventory and required-permission semantics are reviewed.

## Why the Python profiler contract was expanded

Before this experiment, the profiler could map direct methods on a statically constructed class, resolve literal string operation bindings, follow the existing AWS client/resource abstractions, apply the Kubernetes callable-delegation transformation, and execute the Kubernetes stateful resource flow. It did not provide a general SDK-owned typed-state graph equivalent to the Go profiler.

The NATS Python production path requires all of the following:

1. Treat `await` as transparent to static value flow so the result of an awaited mapped factory or method can be assigned.
2. Let a mapped function or constructor produce a typed SDK state with a new dependency identity.
3. Let a mapped receiver method produce another typed state that inherits the receiver's dependency identity.
4. Let a producer bind source-proven values to that returned state so later methods can use them without repeating application arguments.
5. Resolve required and optional bindings from positional arguments, keyword arguments, typed configuration-object fields, and literal string lists without service-specific field names in profiler code.
6. Let one source call reference multiple canonical operations when the SDK source proves multiple requirements, while retaining conservative conditional behavior.
7. Group emitted operations by dependency identity so two separately created NATS clients do not collapse into one Condition.

Adding only an `await` special case would make the top-level factory visible but would not solve JetStream, key/value, object-store, or independent-client behavior. Encoding `bucket`, `name`, or NATS class names directly in the profiler would solve the fixture while creating an SDK-specific profiler maintenance burden.

## Implemented generic mapping contract

The Python mapping now uses the same conceptual primitives already proven in the Go profiler: typed states, factories and calls that produce state, receiver-state requirements, inherited or new dependency identities, argument and typed-field bindings, and explicit operation references. Python syntax resolution remains language-specific, but service meaning remains in the shared service mapping.

A representative authoring shape would be:

```yaml
python:
  factories:
    - id: connect
      symbols:
        - nats.connect
      operationRef: connection.connect
      produces:
        stateType: nats.connection
        dependencyIdentity: new

  calls:
    - id: jetstream
      symbols:
        - module: nats.aio.client
          class: Client
          method: jetstream
      receiverState: nats.connection
      produces:
        stateType: nats.jetstream
        dependencyIdentity: inherit

    - id: key-value
      symbols:
        - module: nats.js.client
          class: JetStreamContext
          method: key_value
      receiverState: nats.jetstream
      operationRef: key_value.inspect
      operationBindings:
        bucket:
          argument:
            parameter: bucket
      produces:
        stateType: nats.key_value
        dependencyIdentity: inherit
        bindings:
          bucket:
            argument:
              parameter: bucket

    - id: key-value-get
      symbols:
        - module: nats.js.kv
          class: KeyValue
          method: get
      receiverState: nats.key_value
      operationRef: key_value.read
      operationBindings:
        bucket:
          state: bucket
```

The generated mapping compiles source parameter names into positional and keyword alternatives so the profiler does not need runtime signature loading. `anyOf` represents multiple SDK-declared sources for one extension field; it never combines those sources into one synthetic service operation. The important constraint is that every name and binding is supplied by SDK metadata and validated against the pinned Python source; none is hard-coded into generic analysis.

## Compatibility requirements

The profiler expansion must remain additive. Existing direct Python SDK mappings, boto3 owner graphs, Kubernetes generated methods, `Watch.stream` delegation, DynamicClient stateful flows, declarative bindings, and application-level composition must continue to pass unchanged. Existing mapping documents must not require migration merely to run the NATS experiment.

## Acceptance result

1. The full pre-existing Python profiler suite passed before integration work, and the expanded suite now passes with AWS, Kubernetes, and NATS fixtures together.
2. The real profiler resolves awaited factories, receiver-produced JetStream state, inherited dependency identity, optional literal lists, typed configuration fields, bucket-bound returned objects, and two independent clients.
3. A required dynamic operation binding emits no operation. It does not widen the condition, insert a placeholder, or fail the application profile.
4. The source projector verifies the pinned release and generates the exact-version mapping twice with byte-identical output.
5. The staged unmodified distribution is discovered without importing or executing NATS SDK code, and all six fixture profiles validate against the exact NATS extension release.
6. The source audit classifies 84 scoped public methods as 44 mapped, 27 excluded, 13 deferred, and zero unclassified. This evidence stays outside the shipped SDK mapping and application profile.
7. Explicit `None` values do not satisfy required fields, do not leak into optional fields, and do not prevent a later declared `anyOf` source from supplying a usable value. Other falsey literal values are preserved.

## What this experiment does not prove

This implementation does not infer arbitrary runtime data flow, prove how many objects a loop or repeatedly invoked factory creates at runtime, or compose state across separately packaged SDK mappings. Dependency identity is based on statically visible construction sites. Typed configuration bindings carry source-proven fields from constructors named by the SDK mapping, but the profiler is not a Python runtime type checker and does not attempt to make invalid SDK calls valid.

Those are deliberate boundaries, not NATS-specific branches. If another valid SDK usage requires one of them, it should motivate a separately reviewed generic profiler contract with cross-SDK regression fixtures. Unknown required values continue to fail closed by omitting the affected operation rather than guessing or broadening a Condition.

## Review focus

The technical question is no longer whether Python can represent these SDK patterns generically; the working fixtures demonstrate that it can. The critical review question is whether the 501-line overlay asks maintainers to review too much mechanical structure. The source projector, service-operation references, and call groups reduce that burden, but this result should be reviewed as evidence for the authoring model rather than accepted automatically as its final ergonomic form.
