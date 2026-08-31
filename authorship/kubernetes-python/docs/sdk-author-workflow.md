# Kubernetes Python SDK author workflow

## First integration

The SDK owner enables one deterministic adjacent generation step after the existing OpenAPI and Python client generation finishes. That step consumes the retained authoritative OpenAPI snapshot, transformed generator input, generated source tree, immutable Kubernetes API extension, and language-neutral service mapping. It emits one distribution-versioned mapping and one concise review summary.

The owner adds the two static package-data paths shown in [`../patches/kubernetes-package-data.patch`](../patches/kubernetes-package-data.patch). No generated client method, application-facing API, SDK runtime dependency, or application source changes.

The local patch proves the artifact path but triggers a current-setuptools warning because nested data directories resemble undeclared namespace packages. The maintainer integration must select a warning-free package-data layout or explicitly declare those data packages; avoiding recurring build noise is part of the acceptance discussion, not an application concern.

The generated typed-client requires no handwritten per-operation annotations. The generator emits 908 authoritative records, 27 separate custom-resource records, one discovery record, 132 explicit list-to-watch overrides, and the synchronous or asynchronous symbols actually present in the release. Each dynamic record fixes its base verb, scope, and optional subresource; only resource coordinates bind from that method's required arguments.

The handwritten surface requires one `Watch.stream` delegation and one DynamicClient resource flow. The projection verifies the wrapper's public symbol, callable parameter, forwarding, target-argument selector, and source assignment. It separately verifies the DynamicClient constructor and `resources` property, the discovery producer and selector forwarding, the Resource method proxy, and the seven public DynamicClient methods against each immutable SDK release.

The DynamicClient authored input describes two constructor aliases, one two-member producer path, three selector bindings, three source-verification locations, seven public methods, and nine fixed operation branches. It contains no built-in resource list. Extension automation generates 95 built-in selectors from authoritative API semantics, and SDK automation generates eight separate state-bound verb templates plus declarative scope-resolution rules.

## Maintainer review

Maintainers review [`../results/python-36.0.3-mapping-review.md`](../results/python-36.0.3-mapping-review.md), generated-source validation failures, extension semantic changes, the focused handwritten-wrapper delegation, and the single DynamicClient flow. They do not review the 944-record mapping YAML or 95-entry selector catalog line by line.

The current authored SDK-owned mapping input is generator logic rather than a method annotation table. The initial retrospective release replay failed on v36.0.0 because the Runtime Conditions projection required an asynchronous generated API directory that did not exist in that release. Correcting the projection to discover the generated flavors present in each release was an authored integration-tooling change. It required no SDK semantic annotation edit, but it still required implementation, review, and regenerated evidence; an upstream SDK integration would ask its maintainers to review and ship that change even if a Runtime Conditions contributor wrote it.

## Recurring release

For each SDK tag, automation resolves the immutable source revision, verifies the retained authoritative and transformed OpenAPI models, verifies every generated public method and argument binding, validates the handwritten delegation and DynamicClient flow against source, regenerates the exact-version mapping and index, validates the target extension digest, builds the package, discovers the installed metadata without SDK imports, and runs representative unchanged applications. An ordinary release with no generated or handwritten semantic drift requires no maintainer-authored mapping edit.

After that tooling repair, the current generator can process four 36.0.x releases, including source validation of the same `Watch.stream` delegation and DynamicClient flow. Version 36.0.0 contains 936 synchronous symbols and no asynchronous surface; versions 36.0.1 through 36.0.3 contain 936 synchronous and 936 asynchronous symbols. The recorded investigation required zero per-operation or per-resource annotation edits, one wrapper delegation, one stateful flow, and one integration-tooling repair.

This was a backward replay using an integration developed against v36.0.3. It proves final compatibility with those historical releases, not zero-touch chronological maintenance, and it does not measure the substantial first-integration work described above. It cannot establish whether a production integration started at v36.0.0 would have needed a change when v36.0.1 introduced the asynchronous surface, because a production implementation might have discovered optional generated flavors from its first release.

## Accepted boundary

The Python profiler discovers the installed mapping without importing Kubernetes, preserves its existing declarative-binding extraction, resolves direct generated calls, composes `Watch.stream` with a statically resolved callable target, carries statically proven DynamicClient resource state into later method calls, validates each result against the exact extension release, and emits nothing for an unresolved callable or resource selector.

The accepted DynamicClient result is intentionally limited to base-resource methods whose statically resolved group/version/kind selector matches one authoritative built-in catalog entry. Source alone does not prove an unmodeled CRD's plural resource name or scope, so that case emits nothing. Dynamic subresources, ResourceList fan-out, constructor-time discovery requests without a resolved resource demand, and other handwritten package behavior remain visible boundaries. They do not prevent this case from answering the cohort's SDK-authoring question, and they are not described as covered.
