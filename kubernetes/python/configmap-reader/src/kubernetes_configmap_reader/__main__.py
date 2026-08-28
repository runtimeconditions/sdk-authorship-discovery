import argparse
import json

from .configmaps import read_config_map


def main() -> None:
    parser = argparse.ArgumentParser(description="Read a Kubernetes ConfigMap with the official Python client")
    parser.add_argument("name")
    parser.add_argument("--namespace", default="default")
    args = parser.parse_args()
    print(json.dumps(read_config_map(args.name, args.namespace), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
