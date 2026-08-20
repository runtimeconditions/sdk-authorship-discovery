# boto3 S3 Resource API

This project uses boto3's higher-level resource API rather than the low-level generated client API:

```python
boto3.resource("s3").Bucket(bucket).put_object(...)
```

It should lead to the same underlying S3 operation requirement as the direct-client case. The mapping architecture must not assume that one service has only one public SDK surface.

Run after installing the project:

```sh
s3-resource-upload my-bucket path/to/key ./local-file
```

