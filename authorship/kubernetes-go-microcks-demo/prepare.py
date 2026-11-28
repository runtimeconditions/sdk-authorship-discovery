"""Acquire one authoritative OpenAPI v3 input; derive explicit mock examples."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / '.cache'
REVISION = '24e2b02af5543d7910c2bb074c7264df5a8f0467'
URL = f'https://raw.githubusercontent.com/kubernetes/kubernetes/{REVISION}/api/openapi-spec/v3/api__v1_openapi.json'
SHA256 = 'a3cbb14c08e7832e80776e717a5658a178dccb3562cc5c1238193634b6985ff8'
VERSION = 'v1.36.2'
POD_PATH = '/api/v1/namespaces/{namespace}/pods'
CONFIG_PATH = '/api/v1/namespaces/{namespace}/configmaps/{name}'
CASES = [(POD_PATH, 'listCoreV1NamespacedPod'), (CONFIG_PATH, 'readCoreV1NamespacedConfigMap')]


def encode(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def documents(raw):
    source = json.loads(raw)
    assert source['openapi'].startswith('3.')
    for path, operation_id in CASES:
        assert source['paths'][path]['get']['operationId'] == operation_id
    sparse = copy.deepcopy(source)
    sparse['info'].update(title='rc-kubernetes-sparse', version=VERSION)
    examples = copy.deepcopy(sparse)
    examples['info']['title'] = 'rc-kubernetes-core'
    values = [
        {'apiVersion': 'v1', 'kind': 'PodList', 'metadata': {}, 'items': []},
        {'apiVersion': 'v1', 'kind': 'ConfigMap', 'metadata': {'name': 'settings', 'namespace': 'demo'}, 'data': {'source': 'microcks-fixture'}},
    ]
    for (path, _), value in zip(CASES, values):
        for parameter in examples['paths'][path].get('parameters', []):
            if parameter.get('in') == 'path':
                fixture = {'namespace': 'demo', 'name': 'settings'}[parameter['name']]
                parameter['examples'] = {'fixture': {'value': fixture}}
        # Keep authoritative schemas, parameters, paths and operation metadata unchanged.
        examples['paths'][path]['get']['responses']['200']['content']['application/json']['examples'] = {'fixture': {'value': value}}
    malformed = copy.deepcopy(examples)
    malformed['info']['title'] = 'rc-kubernetes-malformed'
    for path, _ in CASES:
        malformed['paths'][path]['get']['responses']['200']['content']['application/json']['examples']['fixture']['value'] = 'not-json'
    return {'sparse.json': encode(sparse), 'examples.json': encode(examples), 'malformed.json': encode(malformed)}


def prepare(check=False):
    CACHE.mkdir(exist_ok=True)
    path = CACHE / 'core-v1.json'
    if not path.exists():
        if check:
            raise RuntimeError('missing pinned input; run python3 prepare.py first')
        with urllib.request.urlopen(URL, timeout=60) as response:
            raw = response.read()
        if hashlib.sha256(raw).hexdigest() != SHA256:
            raise RuntimeError('download checksum mismatch')
        path.write_bytes(raw)
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SHA256:
        raise RuntimeError('authoritative input checksum mismatch')
    for name, content in documents(raw).items():
        target = CACHE / name
        if check:
            if not target.exists() or target.read_bytes() != content:
                raise RuntimeError(f'derived input differs: {name}')
        else:
            target.write_bytes(content)
    return json.loads(raw)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    prepare(args.check)
    print('PINNED INPUTS VERIFIED')
