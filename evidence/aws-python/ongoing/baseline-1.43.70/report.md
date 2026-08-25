# AWS Python mapping maintenance report: baseline-1.43.70

## Outcome

**Classification: `automatic`**

The accepted semantic inputs regenerated and passed every requested gate without a handwritten mapping change.

## Release tuple

| Package | Version | Upstream commit |
| --- | --- | --- |
| boto3 | 1.43.70 | `8c2ae687338ebadf80dfd92114e12708304a545d` |
| botocore | 1.43.70 | `144a686dde0a37b694e6b67e073a9c8b4bbc4afe` |
| s3transfer | 0.19.2 | `467a75265eca43937a760c2c169488954df44246` |

## Reproducibility

| Input | Commit | Dirty during run |
| --- | --- | --- |
| sdk | `8248ad007782f249605443dc2916e5dc1692d6dc` | True |
| extensions | `04e7b4fc7a1f511defa199d4efc90312d046000c` | True |

## Generated mapping summary

| Owner | Bytes | Semantic change from accepted baseline | SHA-256 |
| --- | ---: | --- | --- |
| botocore | 40655 | False | `0aca9e31d69f43ce53461d51574710acf3b2f91ac03f0e1ce66c4ffb99103701` |
| s3transfer | 12725 | False | `f47077e19d3175ae59fd2ebc9935ce02dac111a7822734ea008b38399bc824cb` |
| boto3 | 55699 | False | `55f91bb3bc5c42ab26f43c84c51b2f0970ca4140e7a5c173c6cf0fe5482db01a` |

## Gates

| Gate | Status | Duration (seconds) |
| --- | --- | ---: |
| resolve-boto3-source-commit | passed | 0.012 |
| materialize-boto3-source | passed | 0.09 |
| checkout-boto3-source | passed | 0.228 |
| resolve-botocore-source-commit | passed | 0.012 |
| materialize-botocore-source | passed | 0.412 |
| checkout-botocore-source | passed | 0.803 |
| resolve-s3transfer-source-commit | passed | 0.015 |
| materialize-s3transfer-source | passed | 0.051 |
| checkout-s3transfer-source | passed | 0.028 |
| validate-release-compatibility | passed | 0.083 |
| validate-extension-alignment | passed | 0.088 |
| generate-owner-mappings | passed | 0.15 |
| validate-owner-mapping-graph | passed | 0.163 |
| validate-sdk-sources | passed | 0.221 |
| resolve-representative-mapping-paths | passed | 0.141 |
| apply-botocore-package-data | passed | 0.012 |
| stage-botocore-mapping | passed | 0.091 |
| build-botocore-wheel | passed | 7.02 |
| apply-s3transfer-package-data | passed | 0.018 |
| stage-s3transfer-mapping | passed | 0.073 |
| build-s3transfer-wheel | passed | 0.3 |
| apply-boto3-package-data | passed | 0.013 |
| stage-boto3-mapping | passed | 0.112 |
| build-boto3-wheel | passed | 0.389 |
| install-owner-wheels | passed | 1.03 |
| discover-installed-mapping-graph | passed | 0.183 |
| validate-installed-runtime-surfaces | passed | 0.51 |
| check-installed-dependencies | passed | 0.11 |
| test-application-direct-client | passed | 0.267 |
| test-application-session-client | passed | 0.26 |
| test-application-factory-wrapper | passed | 0.273 |
| test-application-dependency-injection | passed | 0.285 |
| test-application-resource-api | passed | 0.304 |
| test-application-dynamic-service | passed | 0.255 |
| test-application-managed-transfer | passed | 0.257 |

## Human review record

- Requested: False
- Reason codes: none
- Disposition: not recorded
- Minutes to understand: not recorded
- Minutes to edit: not recorded
- Minutes to review: not recorded

## Interpretation

This report measures maintenance behavior for the owner-aligned SDK mapping proposal. It does not declare profiler coverage, unresolved application observations, or downstream adapter policy.
