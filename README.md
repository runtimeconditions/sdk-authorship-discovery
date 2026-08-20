# Runtime Conditions SDK Mapping Corpus

This directory contains real, independently runnable applications for investigating how Runtime Conditions profilers should recognize external-resource requirements expressed through SDK usage.

It is a compatibility corpus, not an implementation of an SDK mapping architecture. In particular, nothing here treats the existing `RuntimeConditionsPackage` manifest or current Go SDK extraction behavior as stable.

## Current scope

The first slice uses the published AWS SDK for Python (`boto3==1.43.70`) and the S3 `PutObject` operation. Keeping the service and language fixed lets us compare source patterns without conflating them with different SDK generation systems or language semantics.

All projects:

- use the real boto3 package;
- can upload an object to a real S3 bucket when run with ordinary AWS credentials;
- have tests that exercise the real botocore operation model without making network requests;
- contain no Runtime Conditions annotations, manifests, or declarations;
- are standalone Python projects with their own package metadata.

## Projects

| Project | SDK pattern | Static expectation | Mapping question |
| --- | --- | --- | --- |
| `direct-client` | `boto3.client("s3")` followed by `put_object` | Resolvable | What is the minimum direct-call model? |
| `session-client` | Cross-file `"s3"` constant passed to `Session.client` | Resolvable | How far must constant and receiver resolution reach? |
| `factory-wrapper` | Application factory returns an S3 client | Resolvable | Can effects flow through ordinary application wrappers? |
| `dependency-injection` | Composition root injects an S3 client behind a protocol | Resolvable | Can client identity survive abstraction and injection? |
| `resource-api` | `boto3.resource("s3").Bucket(...).put_object` | Resolvable | Can one service expose multiple public SDK models? |
| `dynamic-service` | Runtime service name passed to `boto3.client` | Unresolved service identity | How should honest ambiguity be reported and remediated? |
| `managed-transfer` | `boto3.client("s3").upload_file(...)` crosses into s3transfer | Resolvable through nested mappings | How are wrapper ownership, receiver configuration, and mutually exclusive transfer paths preserved? |

“Resolvable” is an investigation target, not a claim that the current Python profiler supports the case. “Unresolved” must eventually produce an actionable diagnostic; it must not be silently guessed or silently treated as successful coverage.

## Set up and test

Use Python 3.10 or newer. From this directory:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install \
  -e ./s3/python/direct-client \
  -e ./s3/python/session-client \
  -e ./s3/python/factory-wrapper \
  -e ./s3/python/dependency-injection \
  -e ./s3/python/resource-api \
  -e ./s3/python/dynamic-service \
  -e ./s3/python/managed-transfer
```

Run each project's tests independently:

```sh
python -m unittest discover -s s3/python/direct-client/tests
python -m unittest discover -s s3/python/session-client/tests
python -m unittest discover -s s3/python/factory-wrapper/tests
python -m unittest discover -s s3/python/dependency-injection/tests
python -m unittest discover -s s3/python/resource-api/tests
python -m unittest discover -s s3/python/dynamic-service/tests
python -m unittest discover -s s3/python/managed-transfer/tests
```

Each installed project also exposes a small upload command. For example:

```sh
s3-direct-upload my-bucket path/to/key ./local-file
```

The commands intentionally use boto3's normal credential chain and perform a real S3 request. The tests do neither.

## Expansion policy

The next service should be added only after the S3 investigation produces a defensible mapping model and adopter experience. DynamoDB and SQS are the intended next services because they exercise different resource and operation semantics while remaining within the same generated SDK family.

New languages should be added as separate, independently buildable projects under `s3/<language>/`. Adding a project does not imply that its profiler must immediately support SDK extraction; profiler changes are discussed separately before implementation.

## Documentation obligation

[`docs/sdk-author-experience.md`](docs/sdk-author-experience.md) is the living record of what an SDK author would need to implement. It must change in the same work that changes any proposed SDK mapping contract. Until a contract survives this corpus, it explicitly records that no SDK-author implementation has been accepted.

The investigation is also governed by:

- [`docs/product-constraints.md`](docs/product-constraints.md), which records the adopter and project constraints that architecture proposals must satisfy;
- [`docs/investigation-method.md`](docs/investigation-method.md), which defines how proposals are evaluated;
- [`s3/s3-put-object-ground-truth.md`](s3/s3-put-object-ground-truth.md), which separates what the first boto3 case proves from what an extension must define.

The current SDK-owner authorship proof is under
[`authorship/aws-python`](authorship/aws-python/). It builds owner-aligned
botocore, s3transfer, and boto3 mappings into locally installed wheels,
recursively verifies them without SDK imports, and leaves every application
project unchanged. The earlier combined-boto3 checkpoint remains under
[`authorship/boto3`](authorship/boto3/) because it records the ownership problem
that led to the recursive design.
