# AWS Python mapping maintenance report: ongoing-boto3-1.43.81-botocore-1.43.81-s3transfer-0.19.2

## Outcome

**Classification: `automatic`**

The accepted semantic inputs regenerated and passed every requested gate without a handwritten mapping change.

## Release tuple

| Package | Version | Upstream commit |
| --- | --- | --- |
| boto3 | 1.43.81 | `1ee61ff25b7b2a11577095ac1d478f975c454b1a` |
| botocore | 1.43.81 | `b5c1794f453f0a0a56f3f619baba223d9321a3f9` |
| s3transfer | 0.19.2 | `467a75265eca43937a760c2c169488954df44246` |

## Reproducibility

| Input | Commit | Dirty during run |
| --- | --- | --- |
| sdk | `d89c75ee49145277158d8d4e29383d10cca8d1f3` | False |
| extensions | `83bc9f48e00c4b7073035343b68942834c93f821` | False |
| profiler | `6925a92f782f2b1d6a2cd13c755c908c80cdbddd` | False |

## Generated mapping summary

| Owner | Bytes | Semantic change from accepted baseline | SHA-256 |
| --- | ---: | --- | --- |
| botocore | 40738 | False | `62282ed2bf3b94c3f52c01db7db3ddd751e7bae59507adc5761212b6865581e9` |
| s3transfer | 12808 | False | `e9d5315a7d41a293517b1920f02eea351c5f594d20c3efb2632170c9071abac0` |
| boto3 | 55782 | False | `d6910702babc973a135f61ed47127f0626c2b9db2e7688db13a25ac2652ee8aa` |

## Profiler acceptance profiles

| Application | Semantic match | SHA-256 |
| --- | --- | --- |
| direct-client | True | `592f3ab4e28b466114a7522caff6592af99e326899f9a6835fba1c20e7920385` |
| session-client | True | `54942996978cacf201006c59a40d1e893a9cf7d4196b5862ac71f48112d18253` |
| factory-wrapper | True | `7abb71f0ce9f18d6b01e3dac59c6cbcffbe6f0e1ec696ab2158384331b729bed` |
| dependency-injection | True | `7db774f275e5fe4ef35d98aaceb884182c1a64801e00c955a8dc52e7fa2b74fe` |
| resource-api | True | `332e17b87ff2e48433c7185f4151650e7a6089fc2fe4d6688d64175293b3ce0f` |
| dynamic-service | True | `f9bed231857aa57db95d771a8595ecf53e9d455f6e253ac34cab65d0637d3cc3` |
| managed-transfer | True | `785122b1af14a1c7d57d634e5bedf6f7330c3b776e55f374cf049e35f8918099` |

## Gates

| Gate | Status | Duration (seconds) |
| --- | --- | ---: |
| fetch-boto3-1.43.81 | passed | 0.293 |
| resolve-boto3-1.43.81-commit | passed | 0.002 |
| materialize-boto3-source | passed | 0.131 |
| initialize-botocore-source-cache | passed | 0.003 |
| configure-botocore-source-cache | passed | 0.002 |
| fetch-botocore-1.43.81 | passed | 9.283 |
| resolve-botocore-1.43.81-commit | passed | 0.002 |
| materialize-botocore-source | passed | 0.598 |
| initialize-s3transfer-source-cache | passed | 0.003 |
| configure-s3transfer-source-cache | passed | 0.002 |
| fetch-s3transfer-0.19.2 | passed | 0.355 |
| resolve-s3transfer-0.19.2-commit | passed | 0.002 |
| materialize-s3transfer-source | passed | 0.014 |
| validate-release-compatibility | passed | 0.09 |
| validate-extension-alignment | passed | 0.143 |
| generate-owner-mappings | passed | 0.344 |
| validate-owner-mapping-graph | passed | 0.41 |
| validate-sdk-sources | passed | 0.524 |
| resolve-representative-mapping-paths | passed | 0.333 |
| apply-botocore-package-data | passed | 0.002 |
| stage-botocore-mapping | passed | 0.163 |
| build-botocore-wheel | passed | 4.282 |
| apply-s3transfer-package-data | passed | 0.002 |
| stage-s3transfer-mapping | passed | 0.09 |
| build-s3transfer-wheel | passed | 0.238 |
| apply-boto3-package-data | passed | 0.002 |
| stage-boto3-mapping | passed | 0.209 |
| build-boto3-wheel | passed | 0.266 |
| install-owner-wheels | passed | 1.293 |
| discover-installed-mapping-graph | passed | 0.435 |
| validate-installed-runtime-surfaces | passed | 0.732 |
| check-installed-dependencies | passed | 0.126 |
| test-application-direct-client | passed | 0.452 |
| test-application-session-client | passed | 0.313 |
| test-application-factory-wrapper | passed | 0.317 |
| test-application-dependency-injection | passed | 0.309 |
| test-application-resource-api | passed | 0.333 |
| test-application-dynamic-service | passed | 0.31 |
| test-application-managed-transfer | passed | 0.311 |
| generate-profiler-profile-direct-client | passed | 0.753 |
| compare-profiler-profile-direct-client | passed | 0.002 |
| generate-profiler-profile-session-client | passed | 0.685 |
| compare-profiler-profile-session-client | passed | 0.002 |
| generate-profiler-profile-factory-wrapper | passed | 0.678 |
| compare-profiler-profile-factory-wrapper | passed | 0.002 |
| generate-profiler-profile-dependency-injection | passed | 0.653 |
| compare-profiler-profile-dependency-injection | passed | 0.002 |
| generate-profiler-profile-resource-api | passed | 0.687 |
| compare-profiler-profile-resource-api | passed | 0.002 |
| generate-profiler-profile-dynamic-service | passed | 0.672 |
| compare-profiler-profile-dynamic-service | passed | 0.002 |
| generate-profiler-profile-managed-transfer | passed | 0.73 |
| compare-profiler-profile-managed-transfer | passed | 0.003 |

## Human review record

- Requested: False
- Reason codes: none
- Disposition: not recorded
- Minutes to understand: not recorded
- Minutes to edit: not recorded
- Minutes to review: not recorded

## Interpretation

This report measures maintenance behavior for the owner-aligned SDK mapping proposal. It does not declare profiler coverage, unresolved application observations, or downstream adapter policy.
