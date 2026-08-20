# Dynamically Selected boto3 Service

This project selects the boto3 service from a runtime argument and then calls `put_object`.

It is the negative control for the initial corpus. Several AWS services expose operations named `PutObject`, so a profiler must not infer S3 solely from the method name. Without additional application knowledge, the service identity is unresolved.

The eventual adopter experience should provide an actionable explanation and a small project-local remediation. This project must not be rewritten to make static analysis easier.

It works as an S3 uploader when invoked with `s3`:

```sh
sdk-dynamic-upload s3 my-bucket path/to/key ./local-file
```

