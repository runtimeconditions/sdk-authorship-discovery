# Runtime Conditions SDK mapping corpus

This repository contains independently runnable applications, owner-aligned SDK authorship proofs, and historical and ongoing maintenance experiments for external-resource requirements expressed through SDK usage.

Existing Runtime Conditions package-manifest conventions and profiler behavior are not treated as stable foundations. The current mapping architecture is the result of this corpus and remains subject to SDK-maintainer review before cross-language standardization or profiler adoption.

[`docs/test-cohort.md`](docs/test-cohort.md) defines the accepted cross-architecture cohort: AWS Python, Kubernetes Python, NATS Go, OpenTelemetry Python, OpenFeature Go, and Dapr Java. Cases are investigated sequentially so one SDK family's implementation details do not silently become universal requirements.

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

“Resolvable” is an investigation target rather than a claim that the current Python profiler supports every package-mapping pattern. The profiler now consumes the accepted Kubernetes direct and callable-delegation patterns plus all seven AWS fixtures through client factories, application data flow, resources, and nested owner mappings. Later cohort patterns and unproved SDK surfaces still require integration. Handling incomplete application detection remains a profiler, developer, organization, and downstream-policy decision; the SDK mapping layer does not publish coverage or unresolved observations.

The second model-generated family begins under [`kubernetes`](kubernetes/) with an unchanged application using the official Kubernetes Python client. Its extension and SDK mapping are deliberately separate from the AWS implementation.

[`authorship/kubernetes-python`](authorship/kubernetes-python/) projects the exact Python 36.0.3 generator input into statically verified public SDK symbols, joins generated endpoints back to the authoritative Kubernetes inventory, source-verifies one handwritten `Watch.stream` delegation and one DynamicClient state flow, targets an immutable Kubernetes API extension release, packages the mapping into a locally rebuilt wheel, profiles five unchanged typed and dynamic applications, and replays the 36.0.x release line. Built-in DynamicClient resources resolve through an extension-generated selector catalog; unmodeled CRDs remain silent because static source does not prove the plural resource name or scope supplied by live discovery.

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

[`authorship/kubernetes-python`](authorship/kubernetes-python/) packages the second owner-aligned proof. Start with its [`results/python-36.0.3-mapping-review.md`](authorship/kubernetes-python/results/python-36.0.3-mapping-review.md), [`results/packaging-review.md`](authorship/kubernetes-python/results/packaging-review.md), and [`docs/sdk-author-workflow.md`](authorship/kubernetes-python/docs/sdk-author-workflow.md).

Start with [`authorship/aws-python/REVIEW.md`](authorship/aws-python/REVIEW.md) for the cohesive adoption and maintenance argument. [`docs/sdk-author-experience.md`](docs/sdk-author-experience.md) is the living record of the SDK-author burden and must change whenever the proposed mapping contract changes.

The earlier combined-boto3 checkpoint under [`authorship/boto3`](authorship/boto3/) is retained only because it records the ownership flaw that led to recursive composition.

## Maintenance experiment

[`maintenance/aws-python-s3`](maintenance/aws-python-s3/) defines historical tuples, the ongoing observation cursor, classifications, and durable evidence policy. The runner resolves immutable source, validates package compatibility, regenerates the complete owner graph from accepted extension semantics, runs static or full packaging gates, and distinguishes `automatic`, `extension-review-required`, `sdk-review-required`, and `invalid` outcomes.

The manual historical workflow replays configured releases. The daily ongoing workflow resolves every boto3 release after the live-observation floor plus compatible botocore and s3transfer packages from boto3's source declarations, and it revalidates the latest graph when the selected extension semantic digest changes.

The ten-release historical sample remained automatic after the authoritative Smithy migration. The first ongoing observation—boto3 1.43.79, botocore 1.43.79, and s3transfer 0.19.2—passed the full package, installed-graph, runtime-surface, dependency, and seven-application proof without a semantic mapping change.

The final Kubernetes Python generator processes v36.0.0 through v36.0.3 with no per-operation semantic annotation or binding edit. The investigation itself was not zero-maintenance: the replay excludes the substantial initial integration work, and the initial backward replay then failed on v36.0.0, whose source contained only the synchronous generated surface. The projection required an authored repair to discover the flavors present in each release. This proves compatibility of the repaired generator with the historical sample, not the effort of a chronological production integration.

## Expansion policy

The next investigation axis is SDK architecture rather than another AWS service. The Kubernetes case has now exercised generated methods, dynamic generated endpoints, a higher-order callable wrapper, and a discovery-created stateful resource. NATS is next and will test a primarily handwritten Go client before OpenTelemetry, OpenFeature, and Dapr test exporter, provider, and sidecar delegation models. DynamoDB and SQS remain useful later for expanding service coverage inside the accepted AWS family.

New languages belong in separate independently buildable projects under `s3/<language>/`. Adding a corpus project does not authorize a profiler change; language-profiler expansion is discussed separately before implementation.

The investigation is also governed by [`docs/product-constraints.md`](docs/product-constraints.md), [`docs/investigation-method.md`](docs/investigation-method.md), [`docs/test-cohort.md`](docs/test-cohort.md), and [`s3/s3-put-object-ground-truth.md`](s3/s3-put-object-ground-truth.md).
