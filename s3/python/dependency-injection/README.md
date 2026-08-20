# Dependency-injected S3 Client

This project creates an S3 client at the composition root and injects it into an object writer behind an application-owned protocol.

The target is still automatic resolution. The project tests whether the profiler can preserve SDK client identity through construction, an object field, and a structural interface without requiring Runtime Conditions annotations.

Run after installing the project:

```sh
s3-injected-upload my-bucket path/to/key ./local-file
```

