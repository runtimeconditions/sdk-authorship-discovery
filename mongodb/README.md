# MongoDB driver application corpus

This corpus tests the official MongoDB drivers for Python and Go as one paired SDK-authorship case. Each application uses ordinary driver code, contains no Runtime Conditions declarations, and isolates one source pattern that a future SDK mapping and profiler integration must handle conservatively.

The experiment targets PyMongo 4.18.1 and MongoDB Go Driver 2.9.1. Those releases were published on September 10, 2026. The Go patch release includes a GridFS security fix, so earlier 2.x releases are not used for new fixture work.

## Why this is one paired case

MongoDB publishes common driver specifications and conformance tests, while each driver exposes idiomatic language APIs and maintains its own release. Starting Python and Go together lets us separate cross-driver service meaning from language-specific method, state, callback, and value-flow mechanics before either language becomes the default architecture.

## Fixture matrix

| Application | Python | Go | Question under test |
| --- | --- | --- | --- |
| `constructed-unused` | `MongoClient(..., connect=False)` | `mongo.Connect(...)` without a database operation | Can tooling avoid treating client construction as proof that the application requires a live deployment? |
| `collection-crud` | Dictionary-selected database and collection | `Database(...).Collection(...)` | Can ordinary collection reads and writes retain the literal database and collection selected by application code? |
| `transaction` | `ClientSession.with_transaction` callback | `Session.WithTransaction` callback | Can a transaction enhance the enclosed collection operations without becoming one synthetic operation or losing their namespace demands? |
| `change-stream` | `Collection.watch` | `Collection.Watch` | Can a streaming change subscription enhance the same collection dependency used by transactional reads without inventing a second endpoint? |
| `gridfs` | `GridFSBucket` methods | `GridFSBucket` methods | Can a high-level driver abstraction map to the underlying MongoDB demands without requiring an application developer to understand its internal collections? |
| `two-clients` | Two independently constructed clients | Two independently constructed clients | Can two deployment identities remain two Runtime Conditions rather than being merged by extension shape? |
| `dynamic-namespace` | Runtime database and collection names | Runtime database and collection names | Does analysis remain silent about namespace details it cannot prove instead of inserting placeholders or widening the result? |
| `helper-wrapper` | Application helper returns a collection | Application helper returns a collection | Can source-proven client, database, and collection state survive an ordinary application wrapper? |

The Python and Go applications express the same behaviors, but they are not forced into identical syntax. Differences are evidence for language-profiler and SDK-overlay design.

## Run the applications

The applications perform real MongoDB operations when run and therefore require a reachable deployment. Set `MONGODB_URI` before running a single-client application. `two-clients` requires `MONGODB_ANALYTICS_URI` and `MONGODB_OPERATIONAL_URI`; `dynamic-namespace` additionally requires `MONGODB_DATABASE` and `MONGODB_COLLECTION`.

Install the Python corpus from this directory and run an application directly:

```sh
python -m pip install -e ./python
python ./python/collection-crud/app.py
```

Build every Go application or run one of them:

```sh
cd ./go
go build ./...
go run ./collection-crud
```

The corpus verification used during authorship work compiles every application without requiring a live MongoDB deployment. Live integration testing is a later gate for operation semantics; it is not required merely to prove that a static profiler can parse ordinary application source.

## Current boundary

This phase establishes source authority and application ground truth only. It does not yet define a MongoDB extension, optional source-model supplement, service mapping, SDK overlay, generated mapping, or profiler behavior. The next phase must attempt direct projection from MongoDB's authority and create a supplement only for a documented fact that cannot be derived; the remaining artifacts must follow evidence from the server model and both driver APIs rather than being reverse-engineered from whichever fixture is easiest to support.

The existing `common-integrations` extension can declare a generic `datastore` Condition with `interface.type: document` and `interface.engine: mongodb`. It is intentionally not used as ground truth for this experiment. Whether a future MongoDB extension supersedes that vocabulary, composes with it, or motivates its deprecation will be decided after the adapter-actionable minimum is understood.
