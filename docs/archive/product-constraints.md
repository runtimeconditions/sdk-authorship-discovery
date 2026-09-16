# SDK Mapping Product Constraints

## Status

These constraints govern the SDK mapping investigation. A technically functional design that violates them is not a successful design.

## Primary adopter

The application developer must have the best first experience. Application developers determine whether Runtime Conditions Profiles and SDK integrations are used at all.

The application developer adopts Runtime Conditions to make an application portable between platforms and environments. They should be able to profile locally for inspection and verification, while continuous profile generation normally runs in CI as application code changes.

## Application experience

For a mapped SDK, the application developer should run the language-specific profiler without changing application source.

The maximum recurring application burden is:

- ordinary no-op declaration code for Conditions that cannot be detected through supported SDK mappings;
- an optional project-local override for exceptional cases;
- review of generated output locally and in CI.

If an application only uses a mapped S3 SDK Condition, it should require no no-op declaration code.

The default workflow should not require:

- authoring or understanding SDK symbol mappings;
- a separate compatibility lock duplicating the application's dependency declarations or resolved dependency versions;
- a committed evidence file;
- verbose provenance in ordinary output.

Detailed evidence for emitted Conditions should be available on request, such as through a `--verbose` mode. Detection gaps and the policy for handling them are not part of the mapping artifact.

## Correctness posture

False positives are more damaging than incomplete detection. An incorrectly emitted Condition may cause automation to provision unnecessary resources, incur cloud spend, and leave orphaned infrastructure.

Therefore:

- a mapping must not guess a service or external resource from an ambiguous call;
- ambiguous SDK usage must not produce a Condition unless application code, a conforming mapping, or an explicit developer declaration supplies the missing fact;
- a developer may fill a gap with the no-op declaration package owned by the extension and may report missing SDK coverage upstream;
- whether incomplete coverage warns, blocks CI, or requires acknowledgement belongs to consuming tool or organization policy, not to the SDK mapping's semantic contract.

The mapping layer does not declare coverage percentages or unresolved observations. Developers, platform teams, and downstream adapters decide whether and how to handle incomplete detection.

## Extension boundary

An SDK mapping is conforming only when it targets an existing Runtime Conditions extension and emits data valid under that extension.

Responsibility is divided as follows:

- the extension author owns Condition vocabulary, schemas, validation, and the no-op declaration package;
- an SDK mapper connects SDK services and operations to that extension vocabulary;
- an SDK author is an important stakeholder in choosing whether a vendor-specific or compatible interface is represented;
- an application developer uses the extension's no-op declarations when no suitable SDK mapping exists;
- a downstream adapter decides how a valid Condition is fulfilled on a target platform.

For example, an AWS-owned mapping would reasonably target AWS S3 vocabulary. A downstream adapter may still fulfill that interface using LocalStack or another platform-specific implementation when compatible with the profile requirement.

## SDK author experience

SDK participation cannot be assumed. The integration must offer value without requiring SDK maintainers to participate.

When SDK authors do participate, a one-time model annotation and generator integration can be acceptable. Continuous manual synchronization across services, operations, languages, and ordinary releases is not.

The architecture must not require an SDK to be substantially rewritten. Any proposal that cannot follow the SDK's existing modeling, generation, packaging, governance, and release lifecycle is unsuitable for public recommendation.

## Mapping governance

Repository-owned and community mappings are both legitimate open-source adoption paths. SDK owners should be invited to participate as first adopters, while community mappings allow useful work to proceed without assuming that participation.

Repository ownership establishes the clearest available authority:

- metadata maintained and released by an SDK repository is SDK-owned;
- external metadata is community-owned and must identify its source;
- the SDK's normal maintainers decide whether to adopt, replace, or reject mappings in their repository;
- Runtime Conditions supplies conformance rules and recommendations rather than a central claim of ownership over every SDK mapping.

Exact discovery, conflict, and supersession mechanics remain to be designed and tested.

## Validation path

The intended external validation sequence is:

1. Review the proposed SDK-author workflow with SDK authors.
2. Interview maintainers about adoption and maintenance burden.
3. Integrate with a real SDK or SDK mapping repository.
4. Carry the integration through an actual SDK upgrade.

Passing corpus tests alone is necessary but not evidence of adoption.
