# Kubernetes Python SDK author workflow

## First integration

The SDK owner enables one deterministic adjacent generation step after the existing OpenAPI and Python client generation finishes. That step consumes the retained authoritative OpenAPI snapshot, transformed generator input, generated source tree, immutable Kubernetes API extension, and language-neutral service mapping. It emits one distribution-versioned mapping and one concise review summary.

The owner adds the two static package-data paths shown in [`../patches/kubernetes-package-data.patch`](../patches/kubernetes-package-data.patch). No generated client method, application-facing API, SDK runtime dependency, or application source changes.

The local patch proves the artifact path but triggers a current-setuptools warning because nested data directories resemble undeclared namespace packages. The maintainer integration must select a warning-free package-data layout or explicitly declare those data packages; avoiding recurring build noise is part of the acceptance discussion, not an application concern.

The generated typed-client requires no handwritten per-operation annotations. The generator emits 908 authoritative records, 27 separate custom-resource records, one discovery record, 132 explicit list-to-watch overrides, and the synchronous or asynchronous symbols actually present in the release. Each dynamic record fixes its base verb, scope, and optional subresource; only resource coordinates bind from that method's required arguments.

The handwritten surface currently requires one `Watch.stream` delegation annotation. The projection verifies its public symbol, callable parameter, positional and keyword forwarding, target-argument selector, and source assignment against each immutable SDK release. The annotation contains no Kubernetes resource or endpoint list and does not change when a generated API method is added.

## Maintainer review

Maintainers review [`../results/python-36.0.3-mapping-review.md`](../results/python-36.0.3-mapping-review.md), generated-source validation failures, extension semantic changes, and the focused handwritten-wrapper annotation. They do not review the 936-record mapping YAML line by line.

The current authored SDK-owned mapping input is generator logic rather than a method annotation table. The initial retrospective release replay failed on v36.0.0 because the Runtime Conditions projection required an asynchronous generated API directory that did not exist in that release. Correcting the projection to discover the generated flavors present in each release was an authored integration-tooling change. It required no SDK semantic annotation edit, but it still required implementation, review, and regenerated evidence; an upstream SDK integration would ask its maintainers to review and ship that change even if a Runtime Conditions contributor wrote it.

## Recurring release

For each SDK tag, automation resolves the immutable source revision, verifies the retained authoritative and transformed OpenAPI models, verifies every generated public method and argument binding, validates the handwritten delegation against source, regenerates the exact-version mapping and index, validates the target extension digest, builds the package, discovers the installed metadata without SDK imports, and runs representative unchanged applications. An ordinary release with no generated or handwritten semantic drift requires no maintainer-authored mapping edit.

After that tooling repair, the current generator can process four 36.0.x releases, including source validation of the same `Watch.stream` delegation annotation. Version 36.0.0 contains 936 synchronous symbols and no asynchronous surface; versions 36.0.1 through 36.0.3 contain 936 synchronous and 936 asynchronous symbols. The recorded investigation required zero operation annotation or binding edits, one wrapper delegation annotation, and one integration-tooling repair.

This was a backward replay using an integration developed against v36.0.3. It proves final compatibility with those historical releases, not zero-touch chronological maintenance, and it does not measure the substantial first-integration work described above. It cannot establish whether a production integration started at v36.0.0 would have needed a change when v36.0.1 introduced the asynchronous surface, because a production implementation might have discovered optional generated flavors from its first release.

## Remaining SDK-owned behavior

The package still owns handwritten behavior outside the accepted mapping. `DynamicClient` obtains resource coordinates through discovery-created `Resource` objects, and its methods derive operation behavior from resource state, method arguments, and delegation. This requires focused object-state and application data-flow support; it must not become a broad unconditional Kubernetes requirement or be claimed as covered by the generated mapping.

The Python profiler now discovers the installed mapping without importing Kubernetes, preserves its existing declarative-binding extraction, resolves direct generated calls, composes `Watch.stream` with a statically resolved callable target, validates the result against the exact extension release, and emits nothing for an unresolved callable. `DynamicClient` remains a separate profiler-contract decision.
