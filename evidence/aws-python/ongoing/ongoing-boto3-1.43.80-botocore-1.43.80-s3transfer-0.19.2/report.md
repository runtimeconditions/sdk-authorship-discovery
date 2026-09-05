# AWS Python mapping maintenance report: ongoing-boto3-1.43.80-botocore-1.43.80-s3transfer-0.19.2

## Outcome

**Classification: `automatic`**

The accepted semantic inputs regenerated and passed every requested gate without a handwritten mapping change.

## Release tuple

| Package | Version | Upstream commit |
| --- | --- | --- |
| boto3 | 1.43.80 | `494798148af9c92f2b17b2ac63f342951540cf63` |
| botocore | 1.43.80 | `f60d73ccdf820c1aab8388e5e03f555ccb2a4344` |
| s3transfer | 0.19.2 | `467a75265eca43937a760c2c169488954df44246` |

## Reproducibility

| Input | Commit | Dirty during run |
| --- | --- | --- |
| sdk | `2b54b1230afc6075986b888701ef1b5c91c9ec4b` | False |
| extensions | `e4c228ebab54c294783059772e973a665fc5f3f5` | False |
| profiler | `3c882dbc7427f4c13bd127bc13069e11fc548e67` | False |

## Generated mapping summary

| Owner | Bytes | Semantic change from accepted baseline | SHA-256 |
| --- | ---: | --- | --- |
| botocore | 40738 | False | `07da27088683fb52dc270d5c147d9120fcce78445b186d82db2da0f18f101483` |
| s3transfer | 12808 | False | `e9d5315a7d41a293517b1920f02eea351c5f594d20c3efb2632170c9071abac0` |
| boto3 | 55782 | False | `0d0bf93e7ac22eb0bf158656e3cb801559fa1a2777a0463f6e4a4f8f020609e4` |

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
| fetch-boto3-1.43.80 | passed | 0.586 |
| resolve-boto3-1.43.80-commit | passed | 0.001 |
| materialize-boto3-source | passed | 0.141 |
| initialize-botocore-source-cache | passed | 0.044 |
| configure-botocore-source-cache | passed | 0.031 |
| fetch-botocore-1.43.80 | passed | 12.133 |
| resolve-botocore-1.43.80-commit | passed | 0.001 |
| materialize-botocore-source | passed | 0.417 |
| initialize-s3transfer-source-cache | passed | 0.002 |
| configure-s3transfer-source-cache | passed | 0.006 |
| fetch-s3transfer-0.19.2 | passed | 0.525 |
| resolve-s3transfer-0.19.2-commit | passed | 0.001 |
| materialize-s3transfer-source | passed | 0.009 |
| validate-release-compatibility | passed | 0.071 |
| validate-extension-alignment | passed | 0.104 |
| generate-owner-mappings | passed | 0.235 |
| validate-owner-mapping-graph | passed | 0.282 |
| validate-sdk-sources | passed | 0.363 |
| resolve-representative-mapping-paths | passed | 0.229 |
| apply-botocore-package-data | passed | 0.002 |
| stage-botocore-mapping | passed | 0.114 |
| build-botocore-wheel | passed | 2.894 |
| apply-s3transfer-package-data | passed | 0.002 |
| stage-s3transfer-mapping | passed | 0.066 |
| build-s3transfer-wheel | passed | 0.167 |
| apply-boto3-package-data | passed | 0.001 |
| stage-boto3-mapping | passed | 0.146 |
| build-boto3-wheel | passed | 0.189 |
| install-owner-wheels | passed | 1.275 |
| discover-installed-mapping-graph | passed | 0.3 |
| validate-installed-runtime-surfaces | passed | 0.851 |
| check-installed-dependencies | passed | 0.095 |
| test-application-direct-client | passed | 0.726 |
| test-application-session-client | passed | 0.251 |
| test-application-factory-wrapper | passed | 0.25 |
| test-application-dependency-injection | passed | 0.254 |
| test-application-resource-api | passed | 0.264 |
| test-application-dynamic-service | passed | 0.252 |
| test-application-managed-transfer | passed | 0.253 |
| generate-profiler-profile-direct-client | passed | 0.54 |
| compare-profiler-profile-direct-client | passed | 0.002 |
| generate-profiler-profile-session-client | passed | 0.454 |
| compare-profiler-profile-session-client | passed | 0.002 |
| generate-profiler-profile-factory-wrapper | passed | 0.448 |
| compare-profiler-profile-factory-wrapper | passed | 0.002 |
| generate-profiler-profile-dependency-injection | passed | 0.445 |
| compare-profiler-profile-dependency-injection | passed | 0.002 |
| generate-profiler-profile-resource-api | passed | 0.451 |
| compare-profiler-profile-resource-api | passed | 0.002 |
| generate-profiler-profile-dynamic-service | passed | 0.443 |
| compare-profiler-profile-dynamic-service | passed | 0.001 |
| generate-profiler-profile-managed-transfer | passed | 0.483 |
| compare-profiler-profile-managed-transfer | passed | 0.002 |

## Human review record

- Requested: False
- Reason codes: none
- Disposition: not recorded
- Minutes to understand: not recorded
- Minutes to edit: not recorded
- Minutes to review: not recorded

## Interpretation

This report measures maintenance behavior for the owner-aligned SDK mapping proposal. It does not declare profiler coverage, unresolved application observations, or downstream adapter policy.
