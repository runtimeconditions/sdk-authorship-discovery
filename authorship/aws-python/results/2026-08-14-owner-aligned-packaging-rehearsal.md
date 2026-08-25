# Owner-aligned packaging rehearsal — 2026-08-14

## Outcome

The owner-aligned boto3, botocore, and s3transfer mapping graph was generated,
source-validated, packaged into three local wheels, installed without a
registry, recursively discovered without SDK imports, and exercised by all seven
existing S3 application tests.

No profiler was changed. The six original application projects remained
unchanged; one managed-transfer project was added to retain the deepest nested
mapping path as a future profiler fixture.

## Pinned upstream source

| Repository | Version | Commit |
| --- | --- | --- |
| boto/boto3 | 1.43.70 | `8c2ae687338ebadf80dfd92114e12708304a545d` |
| boto/botocore | 1.43.70 | `144a686dde0a37b694e6b67e073a9c8b4bbc4afe` |
| boto/s3transfer | 0.19.2 | `467a75265eca43937a760c2c169488954df44246` |

s3transfer 0.19.2 was used because it is the version resolved by the unchanged
corpus environment for boto3's `>=0.19.0,<0.20.0` dependency. The initial
minimum-version rehearsal was replaced rather than presented as the normal
resolver outcome.

## Generated inventory

```text
botocore operations: 116
botocore paginators: 8
botocore waiters: 4
boto3 resources: 18
boto3 resource actions: 71
boto3 relations: 37
boto3 collections: 4
boto3 resource waiters: 6
boto3 managed-transfer wrappers: 17
s3transfer logical calls: 4
s3transfer public entrypoints: 9
s3transfer generated operation references: 25
s3transfer distinct canonical operations: 19
```

The generated operation-reference count includes operations repeated across
mutually exclusive execution paths. The distinct count describes the service
operations used by the four logical calls.

## Validation evidence

Static owner-reference validation passed with this dependency order:

```text
botocore: botocore.aws.s3
s3transfer: s3transfer.aws.s3
boto3: boto3.aws.s3
```

Pinned-source validation passed. It also found and rejected one incorrect
handwritten positional binding during development: the metadata placed
`S3Transfer.download_file`'s `extra_args` at position four instead of position
three. The corrected overlay is now guarded by the same check.

Installed-wheel discovery returned the same dependency order and reported:

```yaml
{
  "sdkModulesImported": {
    "boto3": false,
    "botocore": false,
    "s3transfer": false
  }
}
```

Each installed index and mapping digest was checked, and mapping versions were
required to equal their owning installed distributions. `pip check` reported
no broken requirements.

The supplementary installed-SDK test checked all 116 client methods, eight
paginators, four waiters, 19 resource classes, and 148 resource members. It
runtime-checked six s3transfer entrypoints. The three CRT entrypoints were
source-validated but not imported because the optional `awscrt` extra was not
installed in the application environment.

## Artifact measurements

| Mapping | Uncompressed size | SHA-256 |
| --- | ---: | --- |
| boto3 | 97,807 B | `88eddd02d37d646b5a52c09bfae1d51a213f980eb9d11fc98b377e315270f366` |
| botocore | 59,339 B | `71ecd1d4bfdb3be998e50d6c4fc2f29acf59585d5684d1fcd00929d7c0bdf157` |
| s3transfer | 22,638 B | `d866dc9f5e1ee163f3eabc680cec355c5d966e6b51ab1858559d76000f605053` |

| Wheel | Baseline | With mapping | Increase |
| --- | ---: | ---: | ---: |
| boto3 1.43.70 | 140,125 B | 145,307 B | 5,182 B |
| botocore 1.43.70 | 15,594,015 B | 15,598,079 B | 4,064 B |
| s3transfer 0.19.2 | 90,317 B | 92,749 B | 2,432 B |

The total wheel increase was 11,678 bytes.

## Application regression result

All seven tests passed using the rebuilt wheels. The first six applications
remained unchanged; the seventh was added to retain the nested wrapper chain as
a future profiler fixture:

- direct boto3 client;
- session-created client;
- boto3 resource API;
- application-owned client factory;
- dependency-injected client;
- dynamically selected service.
- managed boto3 upload crossing into s3transfer.

The tests use the real SDK operation model with botocore stubs and make no
network requests.

## Recursive behavior examples

The static example resolver successfully followed:

```text
boto3.client("s3").put_object
  -> botocore PutObject
  -> aws.s3 / bucket / PutObject

boto3.resource("s3").Bucket(...).put_object
  -> botocore PutObject
  -> aws.s3 / bucket / PutObject

Bucket.wait_until_exists
  -> botocore bucket_exists waiter
  -> HeadBucket
  -> aws.s3 / bucket / HeadBucket

Bucket.upload_file
  -> s3transfer managed-upload
  -> classic single-part, classic multipart success/abort, or CRT path
  -> owner-qualified botocore operations
  -> aws.s3 / bucket Conditions
```

## Critical interpretation

This proves that version-aligned nested metadata can be delivered with the
existing SDK packages at low package cost and without application work. It does
not prove the candidate is the final cross-language schema or authorize a
profiler implementation. The next review should focus on whether the authored
overlay burden and execution-path model are acceptable to actual maintainers.
