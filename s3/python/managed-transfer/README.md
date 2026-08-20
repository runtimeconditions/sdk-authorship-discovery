# Managed boto3 S3 transfer

This project uses the public `boto3.client("s3").upload_file(...)` helper. The
call is implemented by boto3's handwritten wrapper and s3transfer, so it is the
application fixture for the recursive mapping chain:

```text
boto3 upload_file
  -> s3transfer managed-upload
  -> classic or CRT execution path
  -> botocore S3 operations
  -> AWS S3 extension Conditions
```

The path is selected at runtime from transfer configuration, source properties,
and the available implementation. Mapping metadata preserves those alternatives
without claiming that single-part and multipart operations all execute.

Run after installing the project:

```sh
s3-managed-upload my-bucket path/to/key ./local-file
```

Test the small-file classic path without AWS access:

```sh
python -m unittest discover -s tests
```
