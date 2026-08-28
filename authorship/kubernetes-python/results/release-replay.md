# Kubernetes Python historical release replay

**Classification: `retrospective-compatibility-passed-after-automation-repair`**

The current generator can process 4 of 4 Kubernetes Python releases through the same authoritative join, generated-source verification, extension alignment, and mapping generation. This was a backward compatibility replay using tooling developed against v36.0.3, not a chronological simulation of a production integration. It also does not measure the substantial first-integration work needed to build that tooling.

| Release | Revision | Current generator result | Operations | Sync symbols | Async symbols |
| --- | --- | --- | ---: | ---: | ---: |
| `36.0.0` | `97290c49c18ca84c831068ddb887092353719b3f` | `compatible-with-current-generator` | 936 | 936 | 0 |
| `36.0.1` | `a05fe9e81363ca5ecea656eb6898f059f7a9a60a` | `compatible-with-current-generator` | 936 | 936 | 936 |
| `36.0.2` | `1f2df0359a6f48c20581ccc5f120105b3e99f07f` | `compatible-with-current-generator` | 936 | 936 | 936 |
| `36.0.3` | `67e7d9abfc6fe6629fa650d9b0abf4c99ef8c39c` | `compatible-with-current-generator` | 936 | 936 | 936 |

## Observed investigative maintenance

- **discover-available-generated-flavors**: The initial retrospective replay rejected v36.0.0 because the projection required both synchronous and asynchronous generated API directories, while that release contained only the synchronous flavor. The generator was changed to discover and validate the flavors present in each release. This was real authored integration work, not an SDK semantic annotation change. In an upstream integration, SDK maintainers would still need to review and ship the change even if Runtime Conditions contributors supplied it. Because the experiment began at v36.0.3 and replayed backward, it does not establish exactly when a chronological production integration would have encountered the issue.

## Interpretation

The evidence separates three workloads that must not be collapsed: initial integration construction, which this replay does not measure; 1 authored integration-tooling repair encountered during the replay; and zero per-operation semantic mapping edits observed in the replay. The final generator is backward-compatible with 4 releases. If this integration lived in the SDK repository, its maintainers would need to review and ship an equivalent tooling change, even if Runtime Conditions contributors implemented it.

Release 36.0.0 contains only the synchronous generated surface, while 36.0.1 adds the asynchronous surface. Because the integration was first developed against v36.0.3 and then replayed backward, the experiment cannot establish whether a chronological production integration would have needed the repair at v36.0.0, at v36.0.1, or not at all if flavor discovery had been designed in from the start.

This sample measures final compatibility across patch releases within one Kubernetes API/client major line. It does not prove zero-touch production maintenance and does not substitute for observing future releases as they occur.
