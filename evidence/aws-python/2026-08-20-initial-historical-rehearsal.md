# Initial AWS Python historical maintenance rehearsal — 2026-08-20

## Outcome

The first historical sample processed ten consecutive boto3/botocore releases, 1.43.61 through 1.43.70, against the accepted owner-aligned mapping inputs. All ten static release runs were classified `automatic`: no semantic overlay changed, no human SDK-mapping review was requested, every release tuple satisfied the SDKs' declared dependency ranges, every source/model/reference gate passed, and every generated mapping had the same semantic digest as the accepted baseline after removing generated distribution-version identity.

Full package verification was also run at 1.43.61, 1.43.69, and 1.43.70. All three package runs patched only the static package-data declarations, staged version-aligned mappings, built local boto3/botocore/s3transfer wheels, discovered their mappings without SDK imports, validated installed runtime surfaces and the selected dependency closure, and passed all seven application fixtures.

## Static release sample

| Release | boto3 commit | botocore commit | s3transfer | Classification | Authored mapping change |
| --- | --- | --- | --- | --- | --- |
| 1.43.61 | `8cd8552182da` | `98a8e09f853d` | 0.19.2 | automatic | none |
| 1.43.62 | `f3e9c52bdcef` | `21e1f10479ce` | 0.19.2 | automatic | none |
| 1.43.63 | `db26b21511bf` | `9e1c25a1cfed` | 0.19.2 | automatic | none |
| 1.43.64 | `06a2e1b6c2aa` | `7451e27f30ca` | 0.19.2 | automatic | none |
| 1.43.65 | `b74eb20c9eaa` | `f0f528029935` | 0.19.2 | automatic | none |
| 1.43.66 | `f53e30a443e0` | `32fa45029744` | 0.19.2 | automatic | none |
| 1.43.67 | `ca719c8b0e5f` | `c10ac1e37a0e` | 0.19.2 | automatic | none |
| 1.43.68 | `64ffe2afa675` | `7fb8da784870` | 0.19.2 | automatic | none |
| 1.43.69 | `d59250146a75` | `88995d62c31c` | 0.19.2 | automatic | none |
| 1.43.70 | `8c2ae687338e` | `144a686dde0a` | 0.19.2 | automatic | none |

## Full package checkpoints

| Release | Classification | Requested gates | Result |
| --- | --- | --- | --- |
| 1.43.61 | automatic | 35 | all passed |
| 1.43.69 | automatic | 34 | all passed |
| 1.43.70 | automatic | 34 | all passed |

The variation in gate count reflects the release-compatibility gate being added after the first two endpoint rehearsals; installed dependency closure validation passed in all three. The current runner includes both checks.

## Automation defects found during development

Four failures occurred while building the harness and are excluded from SDK-maintenance measurements because they happened before or outside SDK semantic review:

- A partial bare Git clone could not materialize complete local source. The cache now uses complete depth-one tag snapshots in a shared bare repository.
- Missing local build prerequisites were initially mislabeled as package-integration drift. A runner-prerequisite gate now classifies that as automation-invalid.
- A virtual environment created from another virtual environment did not inherit the parent dependencies. Installed SDK wheels now use an isolated target layered over explicitly validated runner dependencies.
- A global `pip check` inspected unrelated editable application fixtures and reported their deliberate baseline pins. Dependency validation now walks only the closure rooted at boto3, botocore, and s3transfer.

These findings matter to the adoption experiment: infrastructure noise must not be counted as maintainer effort or presented as SDK semantic drift.

## Limits of the result

This is an initial low-drift sample of consecutive boto3/botocore patch releases. It demonstrates that routine releases can be zero-touch, but it does not yet demonstrate the quality of a real semantic-review interruption. The sample holds s3transfer at 0.19.2 and therefore says nothing about maintenance across an s3transfer release boundary. It also does not cross a known S3 service-operation or handwritten-wrapper change.

The runs occurred while the SDK and extensions working trees contained the automation changes described here, so their local reports record dirty inputs. They are development evidence, not the canonical immutable GitHub Actions record. After these changes are committed and pushed, the workflow should be run against an exact extensions commit and its clean reports retained as accepted evidence.

## Next experiment expansion

1. Run the ten-release static sample from GitHub Actions using clean SDK and extension commits.
2. Run the full package proof for the oldest release and baseline from GitHub Actions.
3. Expand backward until the history crosses a real S3 operation-set, boto3 wrapper/resource, or s3transfer behavior change.
4. Add release tuples spanning at least one s3transfer version transition.
5. Record human review time only when a real release produces `review-required`.

The initial result is encouraging but not sufficient for an adoption claim: ten routine releases required zero authored maintenance, while the next sample must test whether the first genuine interruption is precise and tolerable.
