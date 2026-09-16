# Planned SDK Mapping User Experience

## Status

This document records the accepted user experience for discovering third-party SDK mappings and generating Runtime Conditions Profiles. It is a planned implementation contract, not a description of the research prototypes elsewhere in this repository.

The design keeps network access, mapping acquisition, and profile generation separate. A developer, platform engineer, or CI owner chooses whether external mappings are ever resolved.

## Goals

- Ordinary profile generation does not access the network.
- Resolving mappings from a central registry is an explicit operation.
- A profiler never scans dependency source trees to search for mapping files.
- An imported package is not assumed to be an SDK or external integration.
- A missing mapping produces no inferred Condition and no warning by default.
- Extension bindings remain the explicit source-code fallback when automatic mapping is unavailable or unwanted.
- Application dependency resolution remains authoritative for installed package versions; Runtime Conditions does not introduce a second dependency lock.

## Commands

The planned workflow has two independent commands:

```text
runtimeconditions mappings resolve
runtimeconditions profile generate
```

`mappings resolve` is optional and may access a configured mapping registry. `profile generate` is local-only and never invokes the resolver implicitly.

Command spelling may be adapted to a language-specific executable, but implementations MUST preserve the separation between resolution and generation.

## Mapping Resolution

`runtimeconditions mappings resolve` performs the following steps:

1. Parse workload-owned source without entering dependency, vendor, generated-package, or build-output directories.
2. Collect the distinct external package roots referenced by workload source.
3. Resolve the installed version of each referenced package through the language's package manager or compiler metadata.
4. Account for mappings already supplied explicitly, bundled by the SDK, or installed through a companion package.
5. Load or refresh one cached registry catalog for the relevant package ecosystem.
6. Intersect referenced package identities with the catalog locally.
7. Download, validate, and cache mapping artifacts only for positive catalog matches that lack a higher-precedence local mapping.

The resolver MUST NOT:

- recursively inspect `node_modules`, virtual environments, module caches, Maven caches, vendor directories, or equivalent dependency source trees;
- issue one remote request per imported package;
- attempt to classify arbitrary packages as SDKs;
- warn merely because an imported package has no registry entry; or
- generate a mapping by guessing from package names or source code.

The registry catalog is a finite index of mappings that have actually been published. It is not an inventory of every SDK or integration library. A package absent from the catalog remains unclassified and silent.

When the catalog cache is current, resolution may require no catalog request. When it must be refreshed, the resolver performs one catalog request per relevant ecosystem and fetches mapping artifacts only for matches.

## Mapping Sources and Precedence

Mappings may come from four sources:

1. An explicitly selected project-local mapping.
2. A mapping bundled with the installed SDK package.
3. A mapping supplied by an installed companion package.
4. A mapping explicitly resolved from the central registry and stored in the Runtime Conditions cache or an offline bundle.

An explicit local selection overrides the same claimed SDK surface. Without an explicit override, an SDK-bundled mapping takes precedence over a companion or registry mapping, and an installed companion mapping takes precedence over a registry mapping.

Every ecosystem will define a deterministic package-manifest field or exact package-relative mapping location. Discovery performs a direct metadata or path lookup; it never searches package contents recursively.

## Profile Generation

`runtimeconditions profile generate` uses only locally available inputs:

- explicitly selected local mappings;
- mappings bundled with installed SDKs;
- mappings supplied by installed companion packages;
- compatible mappings already present in the Runtime Conditions cache;
- mappings supplied through an explicit offline bundle; and
- extension-binding declarations present in application source.

The generator MUST NOT:

- access a remote registry;
- run `mappings resolve` automatically;
- execute application or dependency code to discover integrations;
- infer a Condition for a package without a resolved mapping; or
- treat absence of a mapping as an error.

If no mapping is available, the package contributes no automatically detected Conditions. The developer may provide an explicit local mapping, use generated extension bindings to declare the Condition, or accept that the Condition is absent.

## Cache and Version Alignment

Registry mappings are cached by package ecosystem, package identity, applicable package version, mapping identity, and content integrity. Before use, profile generation validates a cached mapping against the package version already selected by the application's package manager.

A stale or incompatible cached mapping is not used. The generator does not search remotely for a replacement. A user who wants updated external mappings runs `runtimeconditions mappings resolve` again.

This cache is not a dependency lock and does not select or constrain application dependencies.

## Offline and CI Use

Resolution may optionally produce a portable mapping bundle:

```text
runtimeconditions mappings resolve --bundle <directory>
runtimeconditions profile generate --mappings <directory>
```

The bundle contains only mapping artifacts and the integrity metadata required to verify them. It does not copy application dependencies or introduce another package-version selection mechanism.

A CI workflow may either:

- run `mappings resolve` explicitly before generation;
- restore a trusted Runtime Conditions cache;
- provide a previously resolved mapping bundle; or
- avoid external mappings entirely and rely on bundled, companion, local, or extension-binding declarations.

## Diagnostics

Normal profile generation does not warn about arbitrary packages that lack mappings. Runtime Conditions cannot know whether an unmapped package represents an external integration.

Failures are actionable only after a mapping has positively entered the workflow:

- an explicitly supplied mapping is invalid;
- a package advertises a bundled mapping that cannot be loaded or validated;
- an installed companion mapping is invalid or incompatible;
- a resolved registry artifact fails integrity or extension validation; or
- a supplied cache or bundle claims a mapping that does not match the installed SDK version.

Those cases fail with concise diagnostics. Detailed lookup, selection, validation, and rejection evidence is available through an explicit verbose or diagnostic mode rather than repeated remediation text in ordinary output.

The resolver reports mappings that it resolved or rejected. It does not print one message for every referenced package that lacks a catalog entry.

## Application Experience

An application developer who wants registry mappings runs:

```text
runtimeconditions mappings resolve
runtimeconditions profile generate
```

An application developer who does not want registry access runs only:

```text
runtimeconditions profile generate
```

In both cases, profile generation is deterministic with respect to the application source, resolved dependencies, available local mappings, extension bindings, and selected extensions. Registry resolution changes only which verified mapping artifacts are locally available; it does not change the Condition vocabulary or profile semantics independently of those artifacts.

## Non-Goals

This workflow does not define how SDK mappings are authored, reviewed, published, or maintained. It defines how already-created mappings reach a user and how profile generation consumes them. The SDK-author and central-registry workflow is a separate design problem.
