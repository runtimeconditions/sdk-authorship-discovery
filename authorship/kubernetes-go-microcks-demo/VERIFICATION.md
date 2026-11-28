# Verification report

Updated for container-based Microcks execution and Go 1.26.x portability on branch `demo/microcks-client-go-verification` (PR #10).

## Portability & runtime changes

- Removed host Linux/amd64 checks, `setup_runtime.py` OCI layer extraction, host Java invocation, and `requirements.txt` (`zstandard`).
- Switched `verify.py` to connect to a user- or CI-started `quay.io/microcks/microcks-uber:latest-native` container at `--host` (default `http://127.0.0.1:8585`), without starting or stopping a user's container.
- Added W3C `traceparent` header propagation alongside `X-Trace-Id` in `main.go` and `verify.py`'s unmatched-request control: live testing revealed `quay.io/microcks/microcks-uber:latest-native` (manifest digest `sha256:c0daa6b10aefccb68341828dc98d9fd540f8fd5aa4485ed41c2f428582593d91`, built June 2026) correlates spans via W3C `traceparent` rather than `X-Trace-Id` alone.
- Relaxed `go.mod` (removed `toolchain go1.26.5`), `verify.py`, and `.github/workflows/kubernetes-microcks.yml` to accept any **Go 1.26.x** patch release.
- Preserved pinned Kubernetes `v1.36.2` OpenAPI input (`core-v1.json`) and SHA-256 verification (`prepare.py --check`), plus all positive and negative evidence controls.
- Verified via `quay.io` registry manifest inspection that `quay.io/microcks/microcks-uber:latest-native` publishes both `linux/amd64` and `linux/arm64` images.

## Local verification status (`windows/amd64` host + `linux/amd64` container, Go `1.26.5`, Python `3.13.13`)

- **Passed**:
  - `go test -count=1 ./...`
  - `go vet ./...`
  - `go mod verify`
  - `gofmt -l .`
  - `python prepare.py --check`
  - `python -m unittest -v test_evidence.py` (9/9 tests)
  - `python verify.py --host http://127.0.0.1:18585` and `--out results/evidence.json` (`LIVE MICROCKS VERIFIED` against `quay.io/microcks/microcks-uber:latest-native`, `sha256:c0daa6b10aefccb68341828dc98d9fd540f8fd5aa4485ed41c2f428582593d91`; Windows fallback port `18585` was used after `-p 127.0.0.1:8585:8080` hit a Windows socket permission error and `-p 127.0.0.1:18585:8080` failed to publish on loopback, falling back to `-p 18585:8080`)
  - `tests/test_workflows.py` (3/3 tests when executed with Git Bash `C:\Program Files\Git\usr\bin\bash.exe` instead of the Windows WSL `bash.exe` stub)
  - `git diff --check`
- **Not run / blocked on this host**:
  - `actionlint` (not installed on this Windows host)
  - ARM Mac (`darwin/arm64`) execution has not been run on this machine.

## Observed sparse & malformed behaviour on `latest-native`

- `rc-kubernetes-core`: both `pod-list` and `configmap-get` returned HTTP `200`, matched `listCoreV1NamespacedPod` and `readCoreV1NamespacedConfigMap`, and decoded cleanly (`sdkSuccess=true`, `responseVerified=true`).
- `rc-kubernetes-sparse`: both calls returned HTTP `404` with `operation_not_found` trace events and were rejected by `evidence.py`.
- `rc-kubernetes-malformed`: both calls matched routes (`requestMatched=true`, HTTP `200`) while SDK decoding failed (`sdkSuccess=false`, `responseVerified=false`).

## Commands

```sh
go test -count=1 ./...
python -m unittest -v test_evidence.py
python prepare.py --check
go vet ./...
go mod verify
python verify.py --host http://127.0.0.1:8585
```
