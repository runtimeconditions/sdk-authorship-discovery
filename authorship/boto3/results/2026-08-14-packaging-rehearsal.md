# boto3 1.43.70 packaging rehearsal results

## Scope

This record covers local generation, packaging, installation, and static
discovery. It does not claim that the current Python profiler consumes SDK
mappings, that the candidate schema is accepted, or that all corpus source
patterns are resolved.

## Source identity

- Repository: `https://github.com/boto/boto3.git`
- Tag: `1.43.70`
- Commit: `8c2ae687338ebadf80dfd92114e12708304a545d`
- Mapping boto3 version: `1.43.70`
- Mapping botocore version: `1.43.70`

## Generation

The S3 service mapping and boto3 mapping were regenerated from the installed
botocore 1.43.70 service model, the boto3 1.43.70 resource model, and the
checked-in semantic annotations.

Both outputs matched their checked-in artifacts byte for byte.

Generated inventory:

```text
client factories: 2
client operations: 116
condition templates: 123
resource actions: 47
mapping bytes: 63,510
mapping sha256: 52b42a7df376649c4238b7fa6b38dde17de37c0bde8c0ac79fae572a0339022c
```

## SDK source change

One existing `setup.py` value was reformatted and two package-data patterns
were added. No runtime Python module was changed.

Measured SDK and application burden for this packaging slice:

| Measure | Result |
| --- | ---: |
| Handwritten SDK files changed | 1 |
| SDK diff | 7 insertions, 1 deletion |
| New package-data patterns | 2 |
| Generated SDK files | 2 |
| New SDK runtime dependencies | 0 |
| Application files changed | 0 |
| Application declarations added | 0 |

The shared S3 semantic input was 80 formatted lines. It is not duplicated
inside boto3; the rehearsal stages its generated result.

Generated source-tree additions:

```text
boto3/runtimeconditions/index.yaml                 552 bytes
boto3/runtimeconditions/services/s3.yaml        63,510 bytes
```

## Wheel comparison

Both wheels were built from the same official source with the same Python 3.12
build runtime. Wheel compression makes the generated YAML inexpensive for this
single service:

| Wheel | Compressed bytes |
| --- | ---: |
| Official-source baseline build | 140,125 |
| Runtime Conditions rehearsal build | 144,223 |
| Increase | 4,098 (2.9%) |

The wheel contained both generated Runtime Conditions files and recorded them
in its normal wheel `RECORD` integrity manifest.

Wheel hashes are deliberately not treated as stable outputs because ordinary
wheel timestamps affect byte identity. The service mapping digest in the
generated index is stable.

## Installed discovery

The wheel was installed directly by local path into a copy of the corpus
environment. No registry or application dependency change was used.

The discovery probe:

- found the index through the installed distribution file list;
- checked that index distribution and version matched installed boto3;
- located the S3 mapping through the index;
- verified the mapping digest;
- read the generated inventory;
- confirmed that `boto3` was absent from `sys.modules`.

Result:

```yaml
{
  "distribution": "boto3",
  "version": "1.43.70",
  "index": "boto3/runtimeconditions/index.yaml",
  "sdkImported": false,
  "mappings": [
    {
      "service": "s3",
      "path": "boto3/runtimeconditions/services/s3.yaml",
      "sha256": "52b42a7df376649c4238b7fa6b38dde17de37c0bde8c0ac79fae572a0339022c",
      "extension": "https://runtimeconditions.io/extensions/aws-s3/v1alpha1/runtimeconditions.extension.yaml",
      "clientOperations": 116,
      "resourceActions": 47
    }
  ]
}
```

## Application verification

The existing direct-client project remained unchanged. Its published-style
dependency declaration was still:

```text
boto3==1.43.70
```

Its test passed after the local wheel replaced the original boto3 installation:

```text
Ran 1 test
OK
```

The environment dependency check reported no broken requirements.

## Build observations

The official source still exposes a legacy `setup.py` wheel build. Running it
with a current setuptools version produces deprecation and package-discovery
warnings for boto3's existing data directories as well as the new data
directory. The wheel is produced correctly. An upstream proposal must use
boto3's supported release tooling and should not ask maintainers to adopt this
rehearsal command as a new permanent workflow.

An attempted editable reinstall of the unchanged application in the isolated
copy tried to download its declared build dependency because build isolation
was enabled and network access was disabled. This was unrelated to the SDK
wheel: the application was already installed in the copied corpus environment,
its test ran successfully, and the wheel dependency set was consistent. A
fully offline CI reproduction would place build dependencies in the local
wheelhouse as well.

## Finding that blocks contract acceptance

boto3's dependency declaration permits `botocore>=1.43.70,<1.44.0`. The
low-level S3 client operations and service shapes come from the resolved
botocore package. A mapping generated from botocore 1.43.70 but embedded only
in boto3 1.43.70 is therefore not guaranteed to describe the complete installed
operation owner.

This does not invalidate static SDK packaging. It invalidates the assumption
that one boto3 artifact is automatically version-aligned with every public
surface currently combined in that artifact.
