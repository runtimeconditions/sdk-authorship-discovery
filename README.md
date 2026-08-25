# Runtime Conditions SDK mapping corpus

This repository contains independently runnable applications, an owner-aligned SDK authorship proof, and historical and ongoing maintenance experiments for external-resource requirements expressed through SDK usage.

Existing Runtime Conditions package-manifest conventions and profiler behavior are not treated as stable foundations. The current mapping architecture is the result of this corpus and remains subject to SDK-maintainer review before cross-language standardization or profiler adoption.

## Application corpus

The first slice uses the real AWS SDK for Python and S3. Keeping the service and language fixed lets the investigation compare source patterns without conflating them with unrelated service semantics or language-generation systems.

Every project uses ordinary boto3 code, can perform a real S3 request with normal AWS credentials, has tests that exercise real SDK models without network calls, contains no Runtime Conditions declarations, and builds independently.

| Project | SDK pattern | Static expectation | Mapping question |
| --- | --- | --- | --- |
| `direct-client` | `boto3.client("s3")` followed by `put_object` | Resolvable | What is the minimum direct-call model? |
| `session-client` | Cross-file `"s3"` constant passed to `Session.client` | Resolvable | How far must constant and receiver resolution reach? |
| `factory-wrapper` | Application factory returns an S3 client | Resolvable | Can effects flow through ordinary application wrappers? |
| `dependency-injection` | Composition root injects an S3 client behind a protocol | Resolvable | Can client identity survive abstraction and injection? |
| `resource-api` | `boto3.resource("s3").Bucket(...).put_object` | Resolvable | Can one service expose multiple public SDK models? |
| `dynamic-service` | Runtime service name passed to `boto3.client` | Not statically proven | What application fallback is usable without inventing a dependency? |
| `managed-transfer` | `boto3.client("s3").upload_file(...)` crosses into s3transfer | Resolvable through nested mappings | How are wrapper ownership, receiver configuration, and mutually exclusive execution paths preserved? |

“Resolvable” is an investigation target rather than a claim that the current Python profiler supports package mappings. Handling incomplete application detection remains a profiler, developer, organization, and downstream-policy decision; the SDK mapping layer does not publish coverage or unresolved observations.

## Set up and test the applications

Use Python 3.10 or newer:

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

Run each test suite independently:

```sh
python -m unittest discover -s s3/python/direct-client/tests
python -m unittest discover -s s3/python/session-client/tests
python -m unittest discover -s s3/python/factory-wrapper/tests
python -m unittest discover -s s3/python/dependency-injection/tests
python -m unittest discover -s s3/python/resource-api/tests
python -m unittest discover -s s3/python/dynamic-service/tests
python -m unittest discover -s s3/python/managed-transfer/tests
```

Installed projects also expose small real-upload commands. Those commands intentionally use boto3's normal credential chain; the tests do not make network requests.

## SDK authorship proof

[`authorship/aws-python`](authorship/aws-python/) packages owner-aligned botocore, s3transfer, and boto3 mappings into locally installed wheels, discovers them recursively without SDK imports, validates their exact relationship to an immutable AWS S3 extension release, and leaves application projects unchanged.

Start with [`authorship/aws-python/REVIEW.md`](authorship/aws-python/REVIEW.md) for the cohesive adoption and maintenance argument. [`docs/sdk-author-experience.md`](docs/sdk-author-experience.md) is the living record of the SDK-author burden and must change whenever the proposed mapping contract changes.

The earlier combined-boto3 checkpoint under [`authorship/boto3`](authorship/boto3/) is retained only because it records the ownership flaw that led to recursive composition.

## Maintenance experiment

[`maintenance/aws-python-s3`](maintenance/aws-python-s3/) defines historical tuples, the ongoing observation cursor, classifications, and durable evidence policy. The runner resolves immutable source, validates package compatibility, regenerates the complete owner graph from accepted extension semantics, runs static or full packaging gates, and distinguishes `automatic`, `extension-review-required`, `sdk-review-required`, and `invalid` outcomes.

The manual historical workflow replays configured releases. The daily ongoing workflow resolves every boto3 release after the live-observation floor plus compatible botocore and s3transfer packages from boto3's source declarations, and it revalidates the latest graph when the selected extension semantic digest changes.

The ten-release historical sample remained automatic after the authoritative Smithy migration. The first ongoing observation—boto3 1.43.79, botocore 1.43.79, and s3transfer 0.19.2—passed the full package, installed-graph, runtime-surface, dependency, and seven-application proof without a semantic mapping change.

## Expansion policy

DynamoDB and SQS are the intended next services after the S3 architecture and maintainer experience are accepted. They exercise table, queue, and cross-service semantics while remaining in the same generated SDK family.

New languages belong in separate independently buildable projects under `s3/<language>/`. Adding a corpus project does not authorize a profiler change; language-profiler expansion is discussed separately before implementation.

The investigation is also governed by [`docs/product-constraints.md`](docs/product-constraints.md), [`docs/investigation-method.md`](docs/investigation-method.md), and [`s3/s3-put-object-ground-truth.md`](s3/s3-put-object-ground-truth.md).
