# Candidate recursive SDK mapping contract

This document defines the behavior implemented by the S3 authorship proof. It
is deliberately a candidate: validation and packaging are real, but the field
names are not yet a cross-language specification commitment.

## Distribution index

Every owning Python distribution packages exactly one index at a path ending
in `runtimeconditions/index.json`.

```json
{
  "apiVersion": "runtimeconditions.io/v1alpha1",
  "kind": "RuntimeConditionsSDKMappingIndexCandidate",
  "metadata": {
    "distribution": "boto3",
    "distributionVersion": "1.43.70",
    "language": "python"
  },
  "mappings": [
    {
      "name": "boto3.aws.s3",
      "service": "s3",
      "path": "boto3/runtimeconditions/mappings/aws-s3.json",
      "sha256": "..."
    }
  ]
}
```

A consumer finds the index through installed-distribution metadata, not by
importing the package. The index version and every indexed mapping version must
equal the installed distribution version. The digest protects index-to-mapping
integrity; it is not an application dependency lock.

## Mapping identity and dependencies

Every mapping has an owner-qualified identity:

```json
{
  "metadata": {
    "name": "boto3.aws.s3",
    "distribution": "boto3",
    "distributionVersion": "1.43.70",
    "language": "python",
    "service": "s3"
  },
  "dependencies": [
    {
      "kind": "sdkMapping",
      "distribution": "botocore",
      "mapping": "botocore.aws.s3"
    }
  ]
}
```

An extension dependency uses `kind: extension` and an extension identifier.
SDK mapping dependencies form a directed acyclic graph. A cross-owner reference
must also be declared as a dependency.

No compatible version range appears in this graph. The dependency resolver
selects installed package versions through ordinary application declarations;
the consumer then requires the selected packages to supply self-versioned
mappings.

The mapping graph is not a copy of the complete software dependency graph. A
package becomes a mapping dependency when its owned public behavior contributes
another service/resource semantic step or Runtime Condition. Generic transport,
serialization, retry, and utility packages do not become nodes merely because
they execute at runtime. In the CRT transfer path, s3transfer owns the selected
S3 behavior and awscrt transports it, so the semantic reference terminates at
the botocore S3 operation.

## Typed references

The proof uses three reference types:

```json
{"operationRef": {"distribution": "botocore", "mapping": "botocore.aws.s3", "operation": "PutObject"}}
{"waiterRef": {"distribution": "botocore", "mapping": "botocore.aws.s3", "waiter": "bucket_exists"}}
{"callRef": {"distribution": "s3transfer", "mapping": "s3transfer.aws.s3", "call": "managed-upload"}}
```

Consumers resolve the declared distribution and mapping before member lookup.
Names are not global and are never resolved by best match.

## Public construction and call surfaces

Factory mappings contain every public symbol or alias the owning SDK exposes, a
positional and keyword selector, the accepted service value, and the produced
surface. Resource mappings retain identifiers, actions, relations, collections,
waiters, returned resources, and argument/identifier propagation.

Handwritten wrapper bindings normalize their public arguments before referring
to an underlying logical call:

```json
{
  "method": "upload_file",
  "receiverArguments": {"bucket": "Name"},
  "arguments": {
    "fileobj": {"position": 0, "keyword": "Filename"},
    "key": {"position": 1, "keyword": "Key"}
  },
  "callRef": {
    "distribution": "s3transfer",
    "mapping": "s3transfer.aws.s3",
    "call": "managed-upload"
  }
}
```

Positions exclude the receiver (`self`). Both positional and keyword forms are
recorded because application source can use either. Source validation rejects a
binding when the owning function signature changes.

When behavior depends on state supplied during object construction, a method
binding includes `receiverContext` with the constructor symbol and argument
binding. This is how transfer `config` remains available for classic/CRT and
multipart path reasoning even when the public transfer method receives no
`config` parameter. The generator rejects a wrapper or entrypoint that binds a
logical argument absent from its referenced call.

## Execution paths and predicates

A logical call may have multiple implementations and mutually exclusive paths:

```json
{
  "name": "classic",
  "selection": "classic transfer manager selected by configuration and environment",
  "executionPaths": [
    {
      "name": "single-part",
      "selection": "transfer manager chooses a single request",
      "operationRefs": []
    },
    {
      "name": "multipart-success",
      "selection": "transfer manager chooses multipart and completes successfully",
      "operationRefs": []
    }
  ]
}
```

`selection` is a human-reviewable semantic description in this first proof,
not an instruction to guess a branch. `when` and `whenAll` preserve predicates
on optional follow-up calls. `usage` distinguishes always-on-path, one-or-more,
zero-or-more, and failure-recovery calls.

These are behavioral facts about the SDK. They are not emitted profile fields,
coverage metrics, or unresolved observations. If static application analysis
cannot select a path or prove a predicate, the profiler and its caller decide
whether to omit, widen, warn, request a no-op declaration, or apply another
organization policy.

## Extension boundary

Only the botocore service mapping defines S3 Condition templates. Higher-level
mappings reference canonical operations and cannot invent extension fields.

For `PutObject`, the terminal template is:

```json
{
  "kind": "aws.s3",
  "interfaceType": "bucket",
  "identity": {"source": "input", "path": "Bucket"},
  "operation": {"name": "PutObject"}
}
```

This is an S3 API operation, not an IAM action declaration. Authentication,
environment variables, provisioning policy, and downstream failure behavior
remain outside the SDK mapping unless an extension explicitly defines relevant
vocabulary and application source proves it.

## Required consumer failures

The implemented verifier fails closed for malformed mapping metadata:

- absent index or indexed mapping;
- digest, distribution, or exact version mismatch;
- duplicate mapping identity;
- absent or cyclic dependency;
- undeclared cross-mapping reference;
- missing referenced operation, waiter, or call;
- canonical operation/Condition mismatch.

Those are metadata integrity errors. They are distinct from incomplete
application detection, whose policy remains outside the mapping layer.
