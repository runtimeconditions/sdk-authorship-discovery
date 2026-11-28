# Verify client-go operations with real Microcks traces

A focused follow-up to [issue #8](https://github.com/runtimeconditions/sdk-authorship-discovery/issues/8#issuecomment-7226499577) and the merged [envtest baseline](../kubernetes-go-envtest-demo/). This runs two explicitly authored client-go fixtures against a **Microcks** container (`quay.io/microcks/microcks-uber:latest-native`), then independently reads Microcks' recorded operation spans. It does not generate mapping tables, change the existing profiler, or implement eBPF.

## What this proves

| Authored SDK invocation | Observed request, excluding Microcks' routing prefix | Authoritative operation ID |
| --- | --- | --- |
| `clientset.CoreV1().Pods("demo").List(ctx, metav1.ListOptions{})` | `GET /api/v1/namespaces/demo/pods` | `listCoreV1NamespacedPod` |
| `clientset.CoreV1().ConfigMaps("demo").Get(ctx, "settings", metav1.GetOptions{})` | `GET /api/v1/namespaces/demo/configmaps/settings` | `readCoreV1NamespacedConfigMap` |

Both examples use empty options. A context deadline bounds calls; setting `rest.Config.Timeout` would add a `timeout` query parameter to Get, so the fixture deliberately avoids it. `demo` and `settings` are mock example inputs, not objects created in a real Kubernetes cluster. Microcks returns fixture responses without storing Kubernetes resources.

[main.go](main.go) sets `rest.Config.Host` to the imported service's `/rest/<service>/v1.36.2` prefix. Its `WrapTransport` clones the request, attaches a fresh cryptographically random 32-hex-character `X-Trace-Id` and W3C `traceparent` (`00-<traceId>-<parentSpanId>-01`), and retains only method, escaped path, status and query/transport-error booleans. It never saves headers, credentials, bodies, raw query values or SDK error messages.

[verify.py](verify.py) queries `/api/traces/<traceId>/spans` independently over an administrative HTTP connection. It requires exactly one SDK request and one server operation/invocation span, checks trace isolation, service/version, method and concrete request path, and joins the server's `operation.name` (`GET <path-template>`) to exactly one operation in the authoritative OpenAPI input. **Microcks supplies a method/path operation name, not the Kubernetes `operationId`; the ID and Kubernetes extensions are read from OpenAPI after this verified join.** No expected operation ID is sent in the trace header.

Import, readiness and trace-read traffic use separate administrative requests without the fixture trace ID. No request is redirected through a pretend Microcks server.

## Pinned inputs and container runtime

- Go **1.26.x** (`go.mod` specifies `go 1.26.0` with no `toolchain` pin), client-go/api/apimachinery **v0.36.2**; `go.sum` locks dependencies.
- Kubernetes **v1.36.2**, revision `24e2b02af5543d7910c2bb074c7264df5a8f0467`, [`api/openapi-spec/v3/api__v1_openapi.json`](https://github.com/kubernetes/kubernetes/blob/24e2b02af5543d7910c2bb074c7264df5a8f0467/api/openapi-spec/v3/api__v1_openapi.json).
- Source SHA-256: `a3cbb14c08e7832e80776e717a5658a178dccb3562cc5c1238193634b6985ff8` (2,128,765 bytes, 113 paths, 248 HTTP operations).
- Microcks container image: `quay.io/microcks/microcks-uber:latest-native`. Registry manifest inspection shows both `linux/amd64` and `linux/arm64` variants. Using a moving tag instead of an immutable SHA makes cross-architecture reproduction easier, at the trade-off that future Microcks releases under `latest-native` could change span or importer behaviour.

`prepare.py` checks the source digest before deriving three **complete core-v1 documents**, retaining every path, operation, schema, parameter definition and Kubernetes extension:

| Import | Deliberate changes from authoritative source | Expected behaviour (observed on 1.16.0) |
| --- | --- | --- |
| `rc-kubernetes-sparse` | Only `info.title`/`info.version` for isolated service identity | Both calls return 404; invocation traces exist but contain `operation_not_found`, so no operation mapping is accepted. |
| `rc-kubernetes-core` | Same identity change; named `fixture` examples on the two routes' path parameters (`namespace=demo`, `name=settings` where applicable) and HTTP-200 JSON responses | Both calls match the expected operations, return 200, decode successfully and satisfy fixture-content assertions. |
| `rc-kubernetes-malformed` | Copy of the example-enriched document with its two response example values replaced by deliberately invalid JSON text `not-json` | Both calls still match the expected operations and return 200, but SDK decoding fails. Request matching remains independently observable. |

Microcks' importer needs **path-parameter examples with the same example name as the response**, not only response examples, to register these request/response pairs. The full un-enriched core-v1 import succeeds but is insufficient for these concrete namespaced requests. We do not silently remove optional query parameters or rewrite paths to make matching work.

The container must allow at least 10 MiB per uploaded file and 12 MiB per request (the 2.1 MiB core-v1 OpenAPI file hits HTTP 413 under default Spring multipart limits) and 100% tracing sampling.

## Reproduce

Requires **Docker**, **Go 1.26.x**, and **Python 3.12+** (standard library only; no Python packages or host Java installation required). On Windows or macOS, ensure Docker Desktop is running before starting the container.

### 1. Acquire Go dependencies and pinned OpenAPI inputs

From this directory:

```sh
go mod download all
python prepare.py
```

### 2. Start a dedicated disposable Microcks container

In a separate terminal, start Microcks bound to loopback on port `8585` with multipart upload limits and full tracing sampling enabled:

```sh
docker run --rm -p 127.0.0.1:8585:8080 \
  -e SPRING_SERVLET_MULTIPART_MAX_FILE_SIZE=10MB \
  -e SPRING_SERVLET_MULTIPART_MAX_REQUEST_SIZE=12MB \
  -e MANAGEMENT_TRACING_SAMPLING_PROBABILITY=1.0 \
  -e MANAGEMENT_OTLP_LOGS_EXPORT_ENABLED=false \
  -e OTEL_LOGS_EXPORTER=none \
  -e OTEL_METRICS_EXPORTER=none \
  quay.io/microcks/microcks-uber:latest-native
```

> **Windows fallback:** If `-p 127.0.0.1:8585:8080` fails with a socket permission error on Windows, try `-p 127.0.0.1:18585:8080` first; if Docker Desktop on Windows still fails to expose `127.0.0.1`, fall back to `-p 18585:8080` and pass `--host http://127.0.0.1:18585` to `verify.py`.

### 3. Run unit, integrity, static, and live checks

With network acquisition disabled for Go:

```sh
export GOTOOLCHAIN=local GOPROXY=off GOSUMDB=off GOWORK=off
export GOFLAGS='-mod=readonly -buildvcs=false' CGO_ENABLED=0
go test -count=1 ./...
python -m unittest -v test_evidence.py
python prepare.py --check
go vet ./...
go mod verify
python verify.py --host http://127.0.0.1:8585
```

`verify.py` connects to `--host` (default `http://127.0.0.1:8585`), requires an empty disposable Microcks instance (failing cleanly if fixture or unrelated services already exist), imports all three documents, builds/runs the SDK fixtures, checks positive and negative evidence, and leaves the user-started container running. Stop the container with `Ctrl+C` (or `docker rm -f`) when finished, and start a fresh container before re-running `verify.py`.

Success prints `LIVE MICROCKS VERIFIED` and writes `.cache/evidence.json`. It compares consequential semantics (`observations`, `rejectedControls`, `openapi`, `clientGo`) against the historical snapshot [results/evidence.json](results/evidence.json), ignoring random trace/span IDs and top-level runtime/platform version fields while recording the actual Go version, host OS/architecture, and Microcks image/version in `.cache/evidence.json`. To intentionally update the snapshot after inspecting a run:

```sh
python verify.py --host http://127.0.0.1:8585 --out results/evidence.json
```

## Failure controls and limits

- Missing trace IDs produce a real trace-API 404 and are rejected.
- A real request to an unknown resource produces 404 and no operation match; rejected.
- Two operation spans for one invocation are rejected by an explicit **synthetic duplication of live evidence**; this does not claim Microcks generated ambiguous spans.
- Unit controls also reject cross-trace data, mismatched service/version/method/path, missing/duplicate invocation events, malformed event attributes, multiple requests, queries, transport failure, missing operation IDs, unsupported Go versions, non-loopback/invalid `--host` URLs, and non-empty Microcks instances.
- SDK response success is recorded independently from request matching. A matched route with an SDK decode failure can prove routing; it cannot establish a valid service response or successful operation.
- Fixture attribution remains authored. This does not automatically enumerate/call SDK methods, support all options or resolve wrappers, dynamic clients, CRDs, watches, retries/fan-out or subresources.
- This is an **SDK-authoring test**, not application execution during normal profile generation. It does not resolve mappings, publish a registry artifact or generate a new RC Profile. eBPF is outside this proof.

See [VERIFICATION.md](VERIFICATION.md) for the verification report.
