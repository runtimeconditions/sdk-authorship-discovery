# Extension Binding Auto-Generation

## Required Flow

```text
runtimeconditions.extension.yaml
        +
resolved dependency extensions
        +
language target and publication defaults
        |
        v
generic binding generator
        |
        +-- language-specific no-op source API
        +-- runtimeconditions.bindings.yaml
        +-- package-manager metadata
        +-- extension identity and digest metadata
        +-- generated conformance fixtures
        |
        v
compile + profile-generation test + package-content test
        |
        v
PyPI | Go module | Maven Central | npm | other language registry
```

## Implementation Status

| Component | Status |
| --- | --- |
| Generic extension-to-binding generator | Required target; not implemented |
| Cross-language naming rules in this document | Proposed standard; not implemented |
| Generic `writes[]` manifest instructions | Required profiler contract revision; not implemented |
| Existing Go, Python, and Java binding packages | Handwritten prototypes; inputs for migration tests |

## Inputs

| Input | Required data |
| --- | --- |
| Extension definition | `metadata.id`, `metadata.version`, kinds, interface types, fields, values, schemas, dependencies |
| Dependency closure | Exact immutable definitions named by `spec.dependencies` |
| Core profile schema | Condition fields available to every extension binding |
| Language target | Go, Python, Java, JavaScript/TypeScript, Ruby, Rust, or another supported emitter |
| Publication defaults | Registry namespace, package-name prefix, license, repository URL, minimum language version |
| Generator version | Exact generic generator release |

## Normalized Binding Model

| Extension input | Normalized output |
| --- | --- |
| `metadata.id` | Exact binding-to-extension reference |
| `metadata.version` | Default binding-package release version |
| Canonical extension content | Computed extension integrity pin |
| `spec.dependencies[]` | Imported binding contracts and extension dependency pins |
| `spec.kinds[]` | Condition declaration types |
| `spec.interfaceTypes[]` | Kind-scoped interface constructors |
| `spec.interfaceFields[]` | Interface option paths and value types |
| `spec.conditionFields[]` | Kind/type-scoped additive options |
| `spec.fieldValues[]` | Typed constants, enums, and fixed-value constructors |
| `spec.schemas[]` | Requiredness, scalar types, object shapes, arrays, alternatives, constraints |

## API Derivation Rules

| Extension construct | Generated binding API |
| --- | --- |
| Owned kind | One kind-named declaration accepting typed options |
| Interface type | One typed option fixing `interface.type` |
| Required scalar field | Required constructor or named argument |
| Optional scalar field | Optional typed option or named argument |
| Object field | Typed object constructor with recursively generated members |
| Array field | Repeatable option or language-native collection argument |
| `fieldValues` enum | Language-native enum or exported constants |
| Single fixed field value | Zero-argument fixed-value option |
| `oneOf` | Distinct typed alternatives |
| `anyOf` | Composable typed options |
| Dependency-owned kind or type | Option interfaces implemented against the dependency binding package |
| Additive extension with no owned kind | Option-only package scoped by `appliesToKinds` and `appliesToInterfaceTypes` |

## Core Condition Fields

| Core field | Generated binding API |
| --- | --- |
| `name` | Optional `ConditionName` option |
| `optional` | Optional `Optional` option |

- No positional scalar parameters on kind declarations
- No positional scalar parameters on interface constructors
- Dynamic scalar values accepted only by field-named constructors or language-native named arguments

## Symbol Naming

| Role | Go | Python | Java | TypeScript |
| --- | --- | --- | --- | --- |
| Extension binding namespace | `awss3` | `aws_s3` | `AwsS3` | `awsS3` |
| `aws.s3` kind declaration | `awss3.S3` | `aws_s3.s3` | `AwsS3.s3` | `awsS3.s3` |
| `bucket` interface | `awss3.Bucket` | `aws_s3.bucket` | `AwsS3.bucket` | `awsS3.bucket` |
| `PutObject` operation | `awss3.PutObject` | `aws_s3.put_object` | `AwsS3.putObject` | `awsS3.putObject` |
| Optional Condition name | `awss3.ConditionName` | `aws_s3.condition_name` | `AwsS3.conditionName` | `awsS3.conditionName` |

- Every generated public symbol qualified by the extension binding namespace
- Extension namespace derived from the extension identifier slug
- Application-selected import aliases permitted
- Shortest unique symbol from the full condition-field path
- Parent-path qualification for normalized-name collisions
- Language-standard escaping for reserved words
- Stable ordering by canonical field path, then field value
- Generation failure for unresolved symbol collisions

## Generated Binding Manifest

```yaml
apiVersion: runtimeconditions.io/v1alpha1
kind: RuntimeConditionsBinding
metadata:
  extension: https://runtimeconditions.io/extensions/aws-s3/0.1.0/runtimeconditions.extension.yaml
  extensionSha256: <extension-semantic-digest>
  language: go
go:
  importPath: <stable-go-module-path>
  package: awss3
  declarations:
    - function: S3
      kind: aws.s3
      options:
        - function: ConditionName
          writes:
            - target: name
              argument:
                position: 0
        - function: Bucket
          writes:
            - target: interface.type
              value: bucket
          options:
            - function: PutObject
              writes:
                - target: interface.operations[].name
                  value: PutObject
```

## Generated Language APIs

```go
var _ = awss3.S3(awss3.Bucket(awss3.PutObject()))
```

```python
_ = aws_s3.s3(aws_s3.bucket(aws_s3.put_object()))
```

```java
var ignored = AwsS3.s3(AwsS3.bucket(AwsS3.putObject()));
```

```typescript
const ignored = awsS3.s3(awsS3.bucket(awsS3.putObject()));
```

## Generated Package Contents

| Artifact | Package location |
| --- | --- |
| No-op source API | Language-standard source/package directory |
| Binding manifest | Language-standard Runtime Conditions resource directory |
| Extension definition | Vendored immutable resource or exact registry reference plus digest |
| Package metadata | `pyproject.toml`, `go.mod`, `pom.xml`, `package.json`, gemspec, `Cargo.toml`, or equivalent |
| Conformance fixture | Generated test source using every declaration, option, enum, and alternative |
| Expected profile | Generated YAML fragment for the conformance fixture |

## Profiler Contract

1. Resolve the application dependency graph with the language package manager.
2. Discover binding manifests at the language-standard resource location.
3. Match imported declaration symbols to generated manifest symbols.
4. Evaluate only compile-time values permitted by the binding manifest.
5. Apply generic `writes[].target` instructions to the Condition model.
6. Resolve the exact extension definition from the package, local override, cache, offline bundle, or canonical URI.
7. Verify extension identity, digest, dependency closure, vocabulary, and schema.
8. Emit the Condition and exact extension URI.

## Validation Gates

- Extension schema validation
- Complete dependency resolution
- Required dependency binding package available for the target language
- Deterministic generation check
- Generated source formatting
- Generated source compilation
- Binding-manifest-to-source symbol validation
- Binding-manifest-to-extension vocabulary validation
- Every generated declaration exercised
- Every generated option exercised
- Every generated enum value exercised
- Generated profile schema validation
- Package archive contains required Runtime Conditions resources
- Rebuilt output byte-equivalent to committed output

## Ownership

| Owner | Maintained input |
| --- | --- |
| Extension author | Extension YAML and adapter-actionable semantics |
| Generic tooling maintainers | Normalized model, language emitters, profiler manifest contract, validators |
| Registry maintainers | Publication defaults, signing, immutable hosting, package publication credentials |
| Application developer | Binding package dependency and explicit no-op declarations used by the application |

## Change Processing

```text
extension YAML change
  -> resolve dependency closure
  -> regenerate every supported language package
  -> compare public binding API
  -> classify package version change
  -> compile generated packages
  -> run generated fixtures through real profilers
  -> validate generated profiles
  -> publish extension and binding packages
```

| Change | Generated result |
| --- | --- |
| Added optional field or value | Additive binding API |
| Added required field | Breaking binding API |
| Removed or renamed field/value | Breaking binding API |
| Changed field type or scope | Breaking binding API |
| Schema-only compatible constraint correction | Patch binding release |
| Dependency addition or version change | Regenerated imports and package dependencies |
| Unsupported schema construct | Failed generation; generic generator enhancement required |

## Non-Editable Outputs

- Language-specific no-op source
- `runtimeconditions.bindings.yaml`
- Package-manager metadata derived from publication defaults
- Conformance fixtures
- Expected profiles
- Content digests
