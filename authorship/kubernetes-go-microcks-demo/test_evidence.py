import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from evidence import Rejected, event_attributes, match_openapi, verify_observation
import prepare
import verify

SERVICE = 'rc-kubernetes-core'
TRACE = '0123456789abcdef0123456789abcdef'
TEMPLATE = '/api/v1/namespaces/{namespace}/pods'
PATH = '/rest/rc-kubernetes-core/v1.36.2/api/v1/namespaces/demo/pods'


def positive():
    invocation = {'case': 'pod-list', 'sdkMethod': 'PodInterface.List', 'traceId': TRACE,
                  'requests': [{'method': 'GET', 'path': PATH, 'hasQuery': False, 'transportError': False, 'status': 200}],
                  'sdkSuccess': True, 'responseVerified': True}
    pairs = {'uri.full': 'http://127.0.0.1:1234' + PATH, 'http.method': 'GET', 'query.string': 'empty'}
    data = [part for key, value in pairs.items() for part in ({'key': key}, value)]
    spans = [{'traceId': TRACE, 'spanId': '0123456789abcdef',
              'attributes': {'operation.name': 'GET ' + TEMPLATE, 'operation.method': 'GET',
                             'service.name': SERVICE, 'service.version': 'v1.36.2'},
              'events': [{'name': 'invocation_received', 'attributes': {'data': data}}]}]
    document = {'paths': {TEMPLATE: {'get': {'operationId': 'listCoreV1NamespacedPod', 'x-kubernetes-action': 'list'}}}}
    return invocation, spans, document


class EvidenceTests(unittest.TestCase):
    def test_positive_and_decode_failure_are_separate(self):
        invocation, spans, document = positive()
        result = verify_observation(invocation, spans, document, SERVICE)
        self.assertEqual(result['operationId'], 'listCoreV1NamespacedPod')
        invocation.update(sdkSuccess=False, responseVerified=False)
        result = verify_observation(invocation, spans, document, SERVICE)
        self.assertTrue(result['requestMatched'])
        self.assertFalse(result['sdkSuccess'])

    def test_rejects_unsupported_evidence(self):
        def change_request(key, value):
            return lambda i, s, d: i['requests'][0].update({key: value})

        mutations = {
            'missing spans': lambda i, s, d: s.clear(),
            'cross trace': lambda i, s, d: s[0].update(traceId='1' * 32),
            'zero trace': lambda i, s, d: i.update(traceId='0' * 32),
            'no operation': lambda i, s, d: s[0]['attributes'].pop('operation.name'),
            'ambiguous span': lambda i, s, d: s.append(copy.deepcopy(s[0])),
            'wrong service': lambda i, s, d: s[0]['attributes'].update({'service.name': 'other'}),
            'wrong version': lambda i, s, d: s[0]['attributes'].update({'service.version': 'other'}),
            'wrong method': lambda i, s, d: s[0]['attributes'].update({'operation.method': 'POST'}),
            'wrong operation': lambda i, s, d: s[0]['attributes'].update({'operation.name': 'GET /elsewhere'}),
            'no invocation': lambda i, s, d: s[0]['events'].clear(),
            'duplicate invocation': lambda i, s, d: s[0]['events'].append(copy.deepcopy(s[0]['events'][0])),
            'wrong URI': lambda i, s, d: s[0]['events'][0]['attributes']['data'].__setitem__(1, 'http://127.0.0.1/elsewhere'),
            'missing span id': lambda i, s, d: s[0].pop('spanId'),
            'query': change_request('hasQuery', True),
            'invalid status': change_request('status', 0),
            'second unmatched invocation': lambda i, s, d: s.append({**copy.deepcopy(s[0]), 'attributes': {}}),
            'transport failure': change_request('transportError', True),
            'wrong prefix': change_request('path', '/api/v1/namespaces/demo/pods'),
            'no requests': lambda i, s, d: i['requests'].clear(),
            'multiple requests': lambda i, s, d: i['requests'].append(copy.deepcopy(i['requests'][0])),
            'no OpenAPI match': lambda i, s, d: d['paths'].clear(),
            'no operation ID': lambda i, s, d: d['paths'][TEMPLATE]['get'].pop('operationId'),
            'ambiguous OpenAPI': lambda i, s, d: d['paths'].update({TEMPLATE.replace('{namespace}', '{other}'): copy.deepcopy(d['paths'][TEMPLATE])}),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                invocation, spans, document = positive()
                # A positive control uses exactly the same validator before mutation.
                verify_observation(invocation, spans, document, SERVICE)
                mutate(invocation, spans, document)
                with self.assertRaises(Rejected):
                    verify_observation(invocation, spans, document, SERVICE)

    def test_bad_event_encoding(self):
        for data in ([], {'data': [{}]}, {'data': [None, 'x']}, {'data': [{'key': 'a'}, 1, {'key': 'a'}, 2]}):
            with self.subTest(data=data), self.assertRaises(Rejected):
                event_attributes(data)

    def test_method_and_path_exactness(self):
        _, _, document = positive()
        for method, path in [('POST', '/api/v1/namespaces/demo/pods'), ('GET', '/api/v1/namespaces//pods'), ('GET', '/api/v1/namespaces/demo/pods/')]:
            with self.subTest(method=method, path=path), self.assertRaises(Rejected):
                match_openapi(document, method, path)

    def test_derivations_preserve_authoritative_definitions(self):
        raw = (prepare.CACHE / 'core-v1.json').read_bytes()
        prepare.prepare(check=True)
        source = json.loads(raw)
        for name, encoded in prepare.documents(raw).items():
            derived = json.loads(encoded)
            for key in ('title', 'version'):
                derived['info'][key] = source['info'][key]
            if name != 'sparse.json':
                for path, _ in prepare.CASES:
                    original_path = source['paths'][path]
                    for index, parameter in enumerate(derived['paths'][path].get('parameters', [])):
                        if parameter.get('in') == 'path':
                            parameter.pop('examples', None)
                            if 'examples' in original_path['parameters'][index]:
                                parameter['examples'] = original_path['parameters'][index]['examples']
                    content = derived['paths'][path]['get']['responses']['200']['content']['application/json']
                    content.pop('examples', None)
                    original_content = original_path['get']['responses']['200']['content']['application/json']
                    if 'examples' in original_content:
                        content['examples'] = original_content['examples']
            with self.subTest(name=name):
                self.assertEqual(derived, source)
        # The preservation oracle must also notice an unrelated schema change.
        corrupted = copy.deepcopy(derived)
        corrupted['components']['schemas']['unexpected'] = {'type': 'string'}
        self.assertNotEqual(corrupted, source)

    def test_changed_authoritative_input_rejected(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(prepare, 'CACHE', Path(temporary)):
            (Path(temporary) / 'core-v1.json').write_text('{}')
            with self.assertRaisesRegex(RuntimeError, 'checksum mismatch'):
                prepare.prepare(check=True)

    def test_go_version_acceptance(self):
        for output, expected in [
            ('go version go1.26.5 windows/amd64', 'go1.26.5'),
            ('go version go1.26.0 darwin/arm64', 'go1.26.0'),
            ('go version go1.26 linux/amd64', 'go1.26'),
            ('go version go1.26.12 linux/arm64', 'go1.26.12'),
        ]:
            with self.subTest(output=output):
                self.assertEqual(verify.validate_go_version(output), expected)

        for bad in (
            'go version go1.25.9 linux/amd64',
            'go version go1.27.0 darwin/arm64',
            'go version devel go1.27-abc linux/amd64',
            'not-go-output',
        ):
            with self.subTest(bad=bad), self.assertRaisesRegex(RuntimeError, 'Go 1.26.x'):
                verify.validate_go_version(bad)

    def test_validate_host_normalizes_trailing_slash(self):
        self.assertEqual(verify.validate_host('http://127.0.0.1:8585/'), 'http://127.0.0.1:8585')
        self.assertEqual(verify.validate_host('http://127.0.0.1:8585'), 'http://127.0.0.1:8585')
        for bad in ('https://127.0.0.1:8585', 'http://localhost:8585', 'http://127.0.0.1', 'http://127.0.0.1:8585/api'):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                verify.validate_host(bad)

    def test_ensure_clean_services(self):
        verify.ensure_clean_services([])
        with self.assertRaisesRegex(RuntimeError, 'fixture services already exist'):
            verify.ensure_clean_services([{'name': 'rc-kubernetes-core'}])
        with self.assertRaisesRegex(RuntimeError, 'already has existing services'):
            verify.ensure_clean_services([{'name': 'unrelated-service'}])


if __name__ == '__main__':
    unittest.main()
