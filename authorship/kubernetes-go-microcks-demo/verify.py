"""Connect to a running tagged Microcks container, import inputs, invoke SDKs, verify spans."""
import argparse
import json
import os
from pathlib import Path
import platform
import re
import secrets
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit
from evidence import Rejected, verify_observation, HTTP_METHODS, event_attributes
import prepare

ROOT = Path(__file__).resolve().parent
IMAGE = 'quay.io/microcks/microcks-uber:latest-native'
DEFAULT_HOST = 'http://127.0.0.1:8585'
FIXTURE_SERVICES = ('rc-kubernetes-core', 'rc-kubernetes-sparse', 'rc-kubernetes-malformed')


def validate_go_version(output):
    match = re.search(r'\b(go1\.26(?:\.\d+)?)\b', output)
    if not match:
        raise RuntimeError(f'unsupported Go version {output.strip()!r}; require Go 1.26.x')
    return match.group(1)


def validate_host(host):
    normalized = host.rstrip('/')
    parsed = urlsplit(normalized)
    if (
        parsed.scheme != 'http'
        or parsed.hostname != '127.0.0.1'
        or parsed.port is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError(f'host must be http://127.0.0.1:<port>, got {host!r}')
    return normalized


def ensure_clean_services(services):
    if not isinstance(services, list):
        raise RuntimeError('unexpected /api/services response from Microcks')
    existing = sorted(
        service.get('name', '<unnamed>')
        for service in services
        if isinstance(service, dict) and service.get('name') in FIXTURE_SERVICES
    )
    if existing:
        raise RuntimeError(
            f'fixture services already exist on Microcks ({", ".join(existing)}); '
            'start a fresh disposable container and do not share state across runs'
        )
    if services:
        raise RuntimeError(
            'Microcks instance already has existing services; '
            'use a dedicated disposable Microcks container so unrelated services are untouched'
        )


def request(base, path, data=None, headers=None):
    req = urllib.request.Request(base + path, data=data, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def wait_for_microcks(base, timeout=20):
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        try:
            status, raw = request(base, '/api/services')
            if status == 200:
                ensure_clean_services(json.loads(raw))
                return
            last_error = f'HTTP {status}'
        except urllib.error.URLError as error:
            last_error = str(error.reason)
        time.sleep(0.2)
    raise RuntimeError(
        f'Microcks is not reachable at {base} ({last_error}); start it first with:\n'
        f'  docker run --rm -p 127.0.0.1:8585:8080 '
        f'-e SPRING_SERVLET_MULTIPART_MAX_FILE_SIZE=10MB '
        f'-e SPRING_SERVLET_MULTIPART_MAX_REQUEST_SIZE=12MB '
        f'-e MANAGEMENT_TRACING_SAMPLING_PROBABILITY=1.0 '
        f'{IMAGE}'
    )


def detect_microcks_version(base):
    for path in ('/api/features/config', '/actuator/info'):
        try:
            status, raw = request(base, path)
        except urllib.error.URLError:
            continue
        if status != 200:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            version = data.get('version') or (data.get('build') or {}).get('version')
            if isinstance(version, str) and version:
                return version
    return 'unknown'


def upload(base, name):
    boundary = 'rc-' + secrets.token_hex(16)
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\nContent-Type: application/json\r\n\r\n').encode()
    body += (ROOT / '.cache' / name).read_bytes() + f'\r\n--{boundary}--\r\n'.encode()
    status, _ = request(base, '/api/artifact/upload', body, {'Content-Type': f'multipart/form-data; boundary={boundary}'})
    assert status == 201, f'import failed: {name}, HTTP {status}'


def trace(base, trace_id):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        status, raw = request(base, f'/api/traces/{trace_id}/spans')
        assert status in (200, 404), f'trace API HTTP {status}'
        if status == 200:
            spans = json.loads(raw)
            if any(any(event.get('name') == 'invocation_received' for event in span.get('events', [])) for span in spans):
                return spans
        time.sleep(.05)
    raise AssertionError('missing completed invocation trace')


def rejected(call):
    try:
        call()
    except Rejected as error:
        return str(error)
    raise AssertionError('unsupported evidence accepted')


def normalized_spans(spans):
    # Deliberate allowlist: exclude bodies, addresses, timestamps and raw error text.
    keep = {'service.name', 'service.version', 'operation.name', 'operation.method'}
    result = []
    for span in spans:
        invocations = [event for event in span.get('events', []) if event.get('name') == 'invocation_received']
        if not invocations:
            continue
        if len(invocations) != 1:
            raise Rejected('ambiguous invocation events')
        event = event_attributes(invocations[0]['attributes'])
        uri = urlsplit(event['uri.full'])
        result.append({'traceId': span['traceId'], 'spanId': span['spanId'],
                       'attributes': {key: value for key, value in span.get('attributes', {}).items() if key in keep},
                       'invocation': {'method': event['http.method'], 'path': uri.path, 'hasQuery': bool(uri.query)},
                       'events': [event['name'] for event in span.get('events', [])]})
    return result


def semantic(value):
    if isinstance(value, dict):
        return {
            key: semantic(item)
            for key, item in value.items()
            if key not in ('traceId', 'spanId', 'goVersion', 'microcks', 'platform')
        }
    if isinstance(value, list):
        return [semantic(item) for item in value]
    return value


def run(host, output, timeout=20):
    base = validate_host(host)
    document = prepare.prepare(check=True)
    go = os.environ.get('GO', 'go')
    go_version = validate_go_version(subprocess.check_output([go, 'version'], text=True))
    for name in ('k8s.io/client-go', 'k8s.io/api', 'k8s.io/apimachinery'):
        module = json.loads(subprocess.check_output([go, 'list', '-m', '-json', name], cwd=ROOT, text=True))
        assert module['Version'] == 'v0.36.2' and 'Replace' not in module

    wait_for_microcks(base, timeout=timeout)
    microcks_version = detect_microcks_version(base)

    with tempfile.TemporaryDirectory(prefix='rc-microcks-') as temporary:
        binary_name = 'invoke.exe' if os.name == 'nt' else 'invoke'
        binary = Path(temporary) / binary_name
        subprocess.run([go, 'build', '-mod=readonly', '-o', str(binary), '.'], cwd=ROOT, check=True)

        for name in ('sparse.json', 'examples.json', 'malformed.json'):
            upload(base, name)
        status, raw = request(base, '/api/services')
        assert status == 200
        services = json.loads(raw)
        expected = {method.upper() + ' ' + path for path, item in document['paths'].items() for method in item if method in HTTP_METHODS}
        assert len(services) == 3
        for service in services:
            assert service['version'] == prepare.VERSION
            imported = [operation['name'] for operation in service['operations']]
            assert len(imported) == len(expected) and set(imported) == expected

        observations, rejected_controls = [], []
        seen_traces = set()
        positive = None
        for service in FIXTURE_SERVICES:
            for case, (_, expected_id) in zip(('pod-list', 'configmap-get'), prepare.CASES):
                invocation = json.loads(subprocess.check_output([str(binary), '--host', base, '--service', service, '--case', case], text=True, timeout=20))
                assert invocation['traceId'] not in seen_traces
                seen_traces.add(invocation['traceId'])
                spans = trace(base, invocation['traceId'])
                if service == 'rc-kubernetes-sparse':
                    reason = rejected(lambda: verify_observation(invocation, spans, document, service))
                    assert len(invocation['requests']) == 1 and invocation['requests'][0]['status'] == 404
                    assert not invocation['sdkSuccess'] and not invocation['responseVerified']
                    assert any(event.get('name') == 'operation_not_found' for span in spans for event in span.get('events', []))
                    rejected_controls.append({'control': 'sparse-' + case, 'requestMatched': False,
                                            'invocation': invocation, 'spans': normalized_spans(spans), 'reason': reason})
                else:
                    try:
                        result = verify_observation(invocation, spans, document, service)
                    except Rejected as error:
                        raise AssertionError(f'{service}/{case}: {invocation}') from error
                    assert result['operationId'] == expected_id and result['request']['status'] == 200
                    assert invocation['sdkSuccess'] == (service == 'rc-kubernetes-core')
                    assert invocation['responseVerified'] == (service == 'rc-kubernetes-core')
                    result['service'] = service
                    result['spans'] = normalized_spans(spans)
                    observations.append(result)
                    if positive is None:
                        positive = (invocation, spans)

        missing = secrets.token_hex(16)
        assert missing not in seen_traces
        assert request(base, f'/api/traces/{missing}/spans')[0] == 404
        rejected_controls.append({'control': 'missing-trace', 'httpStatus': 404,
                                'reason': rejected(lambda: verify_observation(positive[0], [], document, 'rc-kubernetes-core'))})

        unknown = '/rest/rc-kubernetes-core/v1.36.2/api/v1/namespaces/demo/not-a-resource'
        trace_id = secrets.token_hex(16)
        status, _ = request(
            base,
            unknown,
            headers={
                'X-Trace-Id': trace_id,
                'traceparent': f'00-{trace_id}-{secrets.token_hex(8)}-01',
            },
        )
        assert status == 404
        spans = trace(base, trace_id)
        invocation = {'case': 'unmatched-control', 'sdkMethod': 'raw HTTP control (not an SDK fixture)', 'traceId': trace_id,
                      'requests': [{'method': 'GET', 'path': unknown, 'status': status, 'transportError': False, 'hasQuery': False}],
                      'sdkSuccess': False, 'responseVerified': False}
        rejected_controls.append({'control': 'unmatched-request', 'invocation': invocation, 'spans': normalized_spans(spans),
                                'reason': rejected(lambda: verify_observation(invocation, spans, document, 'rc-kubernetes-core'))})

        duplicate = positive[1] + [span for span in positive[1] if 'operation.name' in span.get('attributes', {})]
        rejected_controls.append({'control': 'ambiguous-operation-span',
                                'reason': rejected(lambda: verify_observation(positive[0], duplicate, document, 'rc-kubernetes-core'))})

        result = {
            'goVersion': go_version,
            'platform': {'os': platform.system().lower(), 'arch': platform.machine().lower()},
            'microcks': {'version': microcks_version, 'image': IMAGE},
            'clientGo': 'v0.36.2',
            'openapi': {'url': prepare.URL, 'sha256': prepare.SHA256,
                        'pathCount': len(document['paths']), 'operationCount': len(expected)},
            'observations': observations,
            'rejectedControls': rejected_controls,
        }
        snapshot = ROOT / 'results' / 'evidence.json'
        if output.resolve() != snapshot.resolve():
            assert semantic(result) == semantic(json.loads(snapshot.read_bytes())), 'live semantics differ from reviewed snapshot'
        output.parent.mkdir(exist_ok=True, parents=True)
        output.write_bytes(prepare.encode(result))
    print('LIVE MICROCKS VERIFIED')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default=DEFAULT_HOST)
    parser.add_argument('--out', type=Path, default=ROOT / '.cache' / 'evidence.json')
    parser.add_argument('--timeout', type=int, default=20)
    args = parser.parse_args()
    run(args.host, args.out, args.timeout)
