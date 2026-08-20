# Direct boto3 S3 Client

This project is the baseline case: `boto3.client("s3")` and `put_object` occur in the same function.

The expected profiler conclusion is that the workload uses the S3 `PutObject` operation. A profiler must not copy the bucket name, key, body, credentials, or configured region into a Runtime Conditions requirement merely because they are visible at the call site.

Run after installing the project:

```sh
s3-direct-upload my-bucket path/to/key ./local-file
```

Test without AWS access:

```sh
python -m unittest discover -s tests
```

