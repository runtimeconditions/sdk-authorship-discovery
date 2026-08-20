# Application Factory Wrapper

This project keeps boto3 client creation in an application-owned factory and uses the returned client in another module.

The factory is ordinary application code, not a Runtime Conditions integration point. Requiring an annotation on it would make a common refactoring create recurring adoption work, so the target behavior is automatic interprocedural resolution.

Run after installing the project:

```sh
s3-factory-upload my-bucket path/to/key ./local-file
```

