# MongoDB Python and Go SDK authorship review

## Review status

**Source-grounded application corpus complete; extension and SDK mapping design intentionally not started.**

Eight paired Python and Go applications now compile against the current official drivers and exercise the source patterns that should constrain the authorship design. This phase does not claim Runtime Conditions coverage, and it has not created a MongoDB extension, optional source-model supplement, service mapping, SDK overlay, generated SDK mapping, or profiler special case.

That stopping point is deliberate. MongoDB exposes more usable upstream authority than a primarily handwritten SDK such as NATS, but it does not resemble one Smithy or OpenAPI document. Designing the extension from PyMongo methods alone would turn Python implementation details into service semantics; designing it from server commands alone could expose more detail than an adapter can act on. The next phase must establish the join between those sources before any mapping is considered valid.

## Exact experiment inputs

| Input | Version or revision | Role in the experiment |
| --- | --- | --- |
| [`mongodb/mongo-python-driver`](https://github.com/mongodb/mongo-python-driver) | PyMongo 4.18.1, tag commit `127d140440715f2897ccf74d35fec47a32e34af8` | Official Python public surface, parameter names, return-object state, synchronous wrappers, and package boundary |
| [`mongodb/mongo-go-driver`](https://github.com/mongodb/mongo-go-driver) | Go Driver 2.9.1, tag commit `5d8c3a2d65a7ea5c963d85a2d0e7c5b78a1843fa` | Official Go public surface, typed options, return-object state, callbacks, and package boundary |
| [`mongodb/specifications`](https://github.com/mongodb/specifications) | `master` revision `529a2dd14a4fc0e94bb9adca686bbcbdfd15f713` at investigation time | Cross-driver normative behavior and conformance material for CRUD, sessions, transactions, change streams, and GridFS |
| [`mongodb/mongo`](https://github.com/mongodb/mongo) | Stable server release still to be selected | YAML-formatted server IDL containing command names, namespaces, fields, API stability, and—in many cases—authorization access checks |

PyMongo 4.18.1 and Go Driver 2.9.1 were both released on September 10, 2026. Go Driver 2.9.1 fixes a GridFS deletion vulnerability affecting earlier v2 releases, so it is the minimum credible current fixture target rather than an arbitrary preference for the newest tag.

## The authority stack discovered here

MongoDB gives us three upstream layers that must remain distinct:

1. MongoDB Server IDL describes protocol-level commands. For example, `find_command.idl` names the `find` command, declares how its namespace is formed, and includes authorization access checks such as the `find` action on an exact namespace. This is a machine-readable service model candidate and must be evaluated before creating a fallback Service Operations Inventory.
2. MongoDB driver specifications define cross-language behavior that is not represented by one server command. `Collection.watch` is a change-stream abstraction over an aggregation pipeline and cursor continuation; a transaction modifies the execution context of enclosed operations; GridFS is a driver-level file abstraction implemented through multiple collections and operations.
3. Each driver source defines how an application reaches those behaviors in one language. PyMongo uses dictionary access, context managers, and callbacks; the Go driver uses methods, typed option builders, returned state objects, and callbacks. Those are SDK mapping facts, not extension semantics.

The application supplies the final facts: connection selection, concrete database and collection names, independently constructed client identities, and literal options. The profiler may resolve those facts but must not invent them.

This changes the likely upstream workflow. A neutral Operations Inventory is still the last resort, but we cannot yet justify one for MongoDB core commands because the server IDL may already be the stronger authority. The driver specifications are not a replacement inventory: they explain portable driver behavior and wrapper semantics, while the server IDL describes the service operations those behaviors ultimately reach.

## What the fixtures are designed to falsify

| Fixture | Architectural failure it can expose |
| --- | --- |
| `constructed-unused` | Emitting a MongoDB requirement merely because a client object exists, even though current drivers defer meaningful external work until an operation or explicit connectivity check |
| `collection-crud` | Losing database and collection state selected before a later method call, or collapsing read and write demands before the adapter-actionable minimum is reviewed |
| `transaction` | Turning a callback wrapper into one operation with combinatorial parameters, or discarding the separate operations enclosed by the transaction |
| `change-stream` | Treating `watch` as an unrelated endpoint instead of an enhancement of a collection, database, or deployment-scoped MongoDB demand |
| `gridfs` | Forcing application developers to declare internal `files` and `chunks` collections, or hiding the concrete server demands needed by an adapter |
| `two-clients` | Merging two separately configured deployments because their Condition shapes happen to match |
| `dynamic-namespace` | Guessing database or collection names, inserting placeholders, or claiming namespace precision the source does not prove |
| `helper-wrapper` | Requiring Runtime Conditions declarations merely because ordinary application code moves a typed collection through a helper function |

These are not eight proposed extension operations. They are eight application patterns against which the eventual authority, mapping, and profiler contracts must be tested.

## Expected authorship boundary

The experiment should attempt to keep service-level and SDK-level obligations narrow:

| Work | Expected human owner | Expected automation |
| --- | --- | --- |
| MongoDB protocol command definitions and authorization declarations | MongoDB server maintainers through their existing IDL workflow | Project stable public commands, namespaces, fields, and access checks from a pinned server release |
| Cross-driver behavior such as transactions, change streams, and GridFS | MongoDB driver-specification maintainers through their existing specification workflow | Detect relevant specification revisions and validate that direct-projection assumptions still reference accepted behavior |
| Adapter-actionable integration projection | Extension and service stakeholders, potentially including MongoDB maintainers | Compile and validate the authoritative-model projection, using a small supplement only for demonstrated IDL gaps, and publish the immutable extension release |
| Python and Go public symbol/state alignment | Respective driver maintainers or community contributors with their review | Project mechanically declared methods and signatures, validate handwritten associations, and generate final mappings |
| Concrete deployment, database, collection, or bucket values | Application source | Resolve ordinary source values conservatively through the language profiler |

An SDK maintainer should not maintain MongoDB command definitions, authorization rules, extension Condition templates, or a final generated mapping. The likely manual SDK input is limited to the associations and state transformations that cannot be proved from the driver source and cross-driver specifications. This is a hypothesis to measure, not a promise established by the fixture alone.

## Generated versus authored work in this phase

Nothing in this phase is being proposed as an SDK-shipped generated artifact. The repository additions are an investigation record and sixteen ordinary fixture sources, plus one dependency manifest for each language. `go.sum` is ordinary Go dependency resolution output. The successful build does not imply that MongoDB maintainers would own these files.

Later, “generated” must retain its established meaning: deterministic and idempotent tooling output from pinned sources and reviewed semantic inputs. An AI-created method association is not mechanically generated evidence and cannot silently enter the mapping.

## Existing `common-integrations` overlap

The current first-party `common-integrations` extension recognizes MongoDB as `kind: datastore` with `interface.type: document` and `interface.engine: mongodb`, and its no-op bindings let application code declare that generic condition. It has no operation, database, collection, transaction, change-stream, GridFS, or deployment-identity vocabulary.

This experiment does not adapt itself to that existing shape. It also does not modify or deprecate it yet. Once the adapter-actionable minimum is known, we can decide whether a MongoDB-specific extension supersedes the generic condition, composes with it, or demonstrates that the generic feature should be deprecated. Carrying both into profiler output without an explicit relationship would be unacceptable because it could double-provision one application demand.

## Next implementation gate

The next step is to build a narrow, deterministic projection from a pinned stable MongoDB Server release and answer four questions with evidence:

1. Which server IDL commands and authorization declarations cover the CRUD calls in both fixtures, and which relevant commands still live outside IDL or require non-machine-readable interpretation?
2. Can change streams, transactions, and GridFS be expressed as reviewed transformations over those commands without exposing internal implementation detail as application-authored conditions?
3. What is the adapter-actionable minimum: deployment access only, database and collection identity, read/write/watch/transaction capabilities, GridFS bucket identity, or some smaller combination?
4. Does that minimum supersede the generic `common-integrations` MongoDB condition, or can a precise non-duplicative relationship be defined?

The next review should attempt to create the extension release and service mapping directly from MongoDB's IDL and specifications. A semantic supplement should be created only if that attempt identifies an exact integration fact the authority cannot express; the gap and each residual entry must be documented. The Python and Go SDK overlays then become independent joins to the same generated service mapping, followed by real-profiler integration and regression testing. If the IDL proves incomplete as a practical operation authority, the failure itself will justify a MongoDB Service Operations Inventory instead of assuming one in advance.

## Verification completed

- All eight Python applications compile and import against the exact PyMongo 4.18.1 wheel without executing application entry points or contacting MongoDB.
- All eight Go applications build together against MongoDB Go Driver 2.9.1 using Go 1.26.5 and a module declaring Go 1.25 compatibility.
- The fixture sources contain no Runtime Conditions declarations or imports.
- No language profiler, extension, or existing mapping changed in this phase.
