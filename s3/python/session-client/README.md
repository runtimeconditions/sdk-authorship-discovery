# Session-created boto3 S3 Client

This project creates the client through `boto3.Session.client`. The service identifier is a constant imported from another source file.

A useful profiler should resolve this without asking the application developer to repeat `s3` in Runtime Conditions configuration. The case tests cross-file constants and receiver identity together.

Run after installing the project:

```sh
s3-session-upload my-bucket path/to/key ./local-file --profile optional-aws-profile
```

