# boto3 SDK-owner packaging rehearsal

## Status

**Historical checkpoint; superseded by the owner-aligned proof.**

The ownership boundary identified here is now implemented and tested under
[`../aws-python`](../aws-python/). This document remains evidence for why the
complete mapping must not be assigned to boto3 alone.

This rehearsal built boto3 1.43.70 from its official source with the complete
generated S3 mapping embedded as package data. An unchanged application still
passed its boto3 test, and a standalone discovery probe found and verified the
mapping without importing boto3.

The exercise also disproved an important part of the initial packaging
hypothesis: putting the complete mapping in boto3 does not inherently align it
with the installed low-level client operation model. boto3 permits a range of
botocore versions, while botocore owns and loads those service models. The
mapping contract and profiler integration must not be accepted until that
ownership boundary is decided.

No profiler was modified during this rehearsal.

## Question tested

Can an SDK owner ship generated Runtime Conditions metadata inside its normal
Python wheel so that application developers receive it with their existing SDK
dependency and profilers can read it without executing SDK code?

For boto3 packaging, the answer is yes. For placing the entire boto3 and
botocore mapping in that one wheel, the answer is not yet defensible.

## Local package layout

The staging tool adds two generated files to a boto3 source checkout:

```text
boto3/
  runtimeconditions/
    index.json
    services/
      s3.json
```

`index.json` identifies the installed distribution version, locates each
service mapping, identifies its target extension, and records a SHA-256 digest.
`services/s3.json` is the complete generated candidate already maintained under
[`../../../extensions/aws-s3/mappings/boto3`](../../../extensions/aws-s3/mappings/boto3/).

The index is a discovery experiment, not an accepted cross-language contract.

## Exact SDK source change

The only handwritten boto3 source change is
[`boto3-package-data.patch`](boto3-package-data.patch). It adds these patterns
to boto3's existing `package_data` declaration:

```python
'runtimeconditions/index.json',
'runtimeconditions/services/*.json',
```

There are no boto3 runtime imports, public API changes, or Runtime Conditions
dependencies.

## Generated input

The staged S3 mapping is produced by:

- the botocore S3 service model;
- the boto3 S3 resource model;
- the small human-reviewed
  [`semantic-annotations.json`](../../../extensions/aws-s3/model/semantic-annotations.json);
- the existing
  [`generate_mappings.py`](../../../extensions/aws-s3/tools/generate_mappings.py).

Regeneration during the rehearsal produced byte-for-byte equivalents of both
checked-in S3 mapping artifacts.

## Reproduction workflow

Use an isolated checkout of the official boto3 1.43.70 tag. The example
variable names are deliberately task-specific; the checkout and wheel are
disposable and should not be committed.

```sh
git clone --depth 1 --branch 1.43.70 \
  https://github.com/boto/boto3.git \
  /absolute/path/to/boto3-1.43.70

git -C /absolute/path/to/boto3-1.43.70 apply \
  /absolute/path/to/runtimeconditions/sdk/authorship/boto3/boto3-package-data.patch
```

Regenerate the mapping from the pinned service and resource models:

```sh
python /absolute/path/to/runtimeconditions/extensions/aws-s3/tools/generate_mappings.py \
  --service-model /absolute/path/to/botocore/data/s3/2006-03-01/service-2.json.gz \
  --resource-model /absolute/path/to/boto3-1.43.70/boto3/data/s3/2006-03-01/resources-1.json \
  --annotations /absolute/path/to/runtimeconditions/extensions/aws-s3/model/semantic-annotations.json \
  --service-output /absolute/path/to/generated/s3-service-mapping.json \
  --boto3-output /absolute/path/to/generated/runtimeconditions.sdk-mapping.json \
  --boto3-version 1.43.70 \
  --botocore-version 1.43.70
```

Stage the metadata and produce the concise review summary:

```sh
python tools/stage_mapping.py \
  --boto3-source /absolute/path/to/boto3-1.43.70 \
  --mapping /absolute/path/to/generated/runtimeconditions.sdk-mapping.json
```

The rehearsal used boto3's existing wheel build. An upstream integration should
invoke the repository's supported release command rather than standardizing
this experimental command:

```sh
cd /absolute/path/to/boto3-1.43.70
python setup.py bdist_wheel \
  --dist-dir /absolute/path/to/runtimeconditions/sdk/wheelhouse
```

Install the resulting wheel directly by path. No registry is involved:

```sh
python -m pip install --no-deps --force-reinstall \
  /absolute/path/to/runtimeconditions/sdk/wheelhouse/boto3-1.43.70-py3-none-any.whl
```

Finally, run the static discovery probe:

```sh
python tools/discover_mapping.py
```

The probe uses `importlib.metadata` to inspect the installed distribution. It
does not import boto3, load a service model, create a session, or execute SDK
code.

## Human review surface

An SDK maintainer should review:

1. the small semantic annotation change, if service behavior changed;
2. the two-line package-data integration;
3. a concise inventory and digest summary from `stage_mapping.py`;
4. representative application fixtures and expected Conditions;
5. generator failures caused by service-model drift.

The maintainer should not review the generated 63 KB S3 mapping line by line.

The successful S3 staging summary was:

```text
distribution: boto3 1.43.70
service: s3
client factories: 2
client operations: 116
condition templates: 123
resource actions: 47
mapping sha256: 52b42a7df376649c4238b7fa6b38dde17de37c0bde8c0ac79fae572a0339022c
```

## Application proof

The local wheel replaced the published boto3 wheel in a copy of the corpus
environment. The application source and its `boto3==1.43.70` declaration were
unchanged.

The discovery probe reported:

```json
{
  "distribution": "boto3",
  "version": "1.43.70",
  "sdkImported": false,
  "mappings": [
    {
      "service": "s3",
      "clientOperations": 116,
      "resourceActions": 47
    }
  ]
}
```

The direct-client application test passed using the rebuilt wheel, and the
environment's installed dependency set remained consistent.

Detailed measurements are in
[`results/2026-08-14-packaging-rehearsal.md`](results/2026-08-14-packaging-rehearsal.md).

## Critical ownership and version finding

boto3 1.43.70 declares:

```text
botocore>=1.43.70,<1.44.0
```

The application pins boto3 1.43.70, but dependency resolution may install a
later compatible botocore release. botocore owns the service model and creates
the low-level service clients dynamically. Therefore:

- the 116 low-level S3 operations are aligned to botocore 1.43.70, not solely
  to boto3 1.43.70;
- a later resolved botocore can expose operations absent from the mapping
  embedded in the unchanged boto3 wheel;
- a changed operation shape could invalidate an input identity path even though
  the boto3 version has not changed;
- the application has no second compatibility lock, and adding one solely for
  Runtime Conditions would violate the adopter constraints.

The current mapping also combines several ownership layers:

- boto3 top-level client factories;
- botocore-generated low-level client operations;
- boto3 resource-model actions.

Packaging all three in boto3 is convenient, but convenience is not evidence
that boto3 is the correct versioning authority for all three.

## Other contract gaps exposed by the source checkout

The wheel proves delivery, not that the current mapping describes enough of
boto3's public construction model. Before accepting the mapping contract, it
must also address:

- `serviceNameArgument: 0` describes the positional factory argument but not
  the supported `service_name="s3"` keyword form;
- the mapping names `boto3.session.Session.client`, while boto3 publicly
  re-exports that class as `boto3.Session`; the contract must say whether SDK
  metadata lists public aliases or profilers resolve re-exports;
- the resource-action list names classes such as `Bucket`, but the mapping has
  no resource-factory or construction-chain metadata connecting
  `boto3.resource("s3").Bucket(...)` to those actions;
- handwritten transfer and convenience wrappers remain absent, as already
  recorded in the S3 mapping documentation.

These gaps do not affect the successful direct-client packaging test. They do
mean that the current 47 generated resource actions are not yet sufficient to
profile the corpus's resource API application.

## Recommended correction

Split generated metadata according to the package that owns each public
surface:

1. botocore ships canonical service operation mappings generated with its
   service models;
2. boto3 ships factory, resource-model, and handwritten-wrapper bindings that
   reference those canonical operations;
3. the profiler discovers both installed distributions and composes their
   static metadata;
4. each artifact is automatically aligned to the version of its owning
   installed package.

This retains the application experience: both packages are already present,
there is no manual mapping installation, and neither package gains a runtime
dependency. It does add a mapping-composition responsibility to profilers and
asks two related package release paths to include metadata.

## Alternatives requiring explicit rejection or acceptance

### Keep the entire mapping in boto3

This is the smallest packaging change. Known operations remain usable, and a
new botocore operation would normally create an incomplete result rather than
a false Condition. It still leaves potential model-shape drift and makes the
artifact less authoritative than the installed operation owner.

### Put everything in botocore

This aligns low-level operations but makes botocore claim knowledge of boto3's
resource and wrapper APIs. That reverses the actual dependency direction and
should be rejected.

### Publish a mapping for each boto3/botocore version pair

This can be done externally, but creates selection, publication, and automatic
installation work and risks a combinatorial maintenance surface. It is useful
as a community fallback, not the preferred SDK-owned design.

## Decision gate

Before defining the mapping schema or changing the Python profiler, decide
whether the first accepted experiment will:

- split ownership between botocore and boto3 as recommended; or
- deliberately accept conservative incompleteness and model-shape risk by
  retaining the complete mapping in boto3.

The packaged index and service file remain candidates until that decision is
made.

## Rehearsal files

- [`boto3-package-data.patch`](boto3-package-data.patch) is the exact SDK build
  change used in the local wheel.
- [`tools/stage_mapping.py`](tools/stage_mapping.py) validates version identity,
  stages the generated mapping, creates its index, and prints the review
  summary.
- [`tools/discover_mapping.py`](tools/discover_mapping.py) proves installed
  static discovery and digest verification without importing boto3.
- [`results/2026-08-14-packaging-rehearsal.md`](results/2026-08-14-packaging-rehearsal.md)
  records the performed build and its limitations.
