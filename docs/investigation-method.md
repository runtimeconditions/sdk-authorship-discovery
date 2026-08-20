# SDK Mapping Investigation Method

## Purpose

The corpus exists to falsify SDK mapping designs against ordinary source code and explicit adopter-experience constraints. It must not be changed merely to make a proposed profiler implementation easier.

## Priority order

Designs are evaluated in this order:

1. Adopter experience, measured separately for application developers and SDK authors
2. Capability and source-pattern coverage
3. Mapping maintainer experience
4. Profiler implementation convenience

Profiler convenience cannot justify recurring work for every application or every SDK release.

## Application-adopter budget

For a supported SDK and statically resolvable usage, the target is:

- no application source edits;
- no Runtime Conditions declaration calls;
- no manual SDK mapping installation;
- no knowledge of the SDK's generated internal types;
- an explanation for every emitted Condition.

The explanation should be available on request through verbose output. Ordinary output should keep the generated profile concise. The mapping layer does not emit coverage percentages or unresolved observations; application tooling and organizational policy decide whether and how to investigate incomplete detection.

When no conforming SDK mapping exists, the supported application fallback is the no-op declaration package published for the relevant extension. A project-local override may also be supported, but application developers should not be asked to author SDK symbol mappings or copy an SDK-wide operation table into their project.

## SDK-author budget

The investigation must measure:

- files added to the SDK source repository;
- human-authored lines and concepts;
- whether metadata can be generated from the SDK's source model;
- release steps added to every SDK language;
- work required when an operation is added, renamed, or regenerated;
- tests SDK authors must own;
- compatibility promises SDK authors are being asked to make.

A design that requires equivalent method lists to be maintained independently in every generated SDK is presumed unacceptable unless evidence shows no viable alternative.

## Evaluation record for each project

Every attempted mapping architecture should record:

1. Which SDK construction expression established service identity.
2. Which operation expression established the external effect.
3. What source and package versions were consulted.
4. Whether each emitted conclusion was proven, inferred, or explicitly configured.
5. Which application, SDK-author, and mapping-maintainer actions were required.
6. What would invalidate the mapping after an SDK upgrade.

This is an investigation record for evaluating designs, not a proposed mapping or profile output schema.

## Acceptance gate for the S3 slice

The S3 slice is not complete until one architecture:

- handles all five resolvable projects without source modification;
- does not guess an S3 Condition for `dynamic-service`, and documents the no-op declaration as the small manual fallback;
- does not execute application or dependency code during analysis;
- derives language-specific SDK symbols mechanically where the source model permits it;
- explains exactly what an SDK author publishes and maintains;
- proves compatibility with the boto3 version already selected by the application's dependency resolution, without requiring a second compatibility lock;
- distinguishes a detected SDK operation from a concrete bucket, account, credential, or deployment value.
