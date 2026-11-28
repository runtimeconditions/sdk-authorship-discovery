"""Fail-closed join of client observation, independent Microcks span, and OpenAPI."""
import re
from urllib.parse import urlsplit

HTTP_METHODS = {'get', 'post', 'put', 'delete', 'patch', 'head', 'options', 'trace'}


class Rejected(ValueError):
    pass


def match_openapi(document, method, concrete_path):
    matches = []
    for template, item in document['paths'].items():
        parts = template.split('/')
        pattern = '/'.join('[^/]+' if re.fullmatch(r'\{[^{}]+\}', part) else re.escape(part) for part in parts)
        if method.lower() in item and re.fullmatch(pattern, concrete_path):
            operation = item[method.lower()]
            if not operation.get('operationId'):
                raise Rejected('missing operationId')
            matches.append((template, operation))
    if len(matches) != 1:
        raise Rejected(f'expected one OpenAPI operation, found {len(matches)}')
    return matches[0]


def event_attributes(attributes):
    # Microcks 1.16.0 serializes EventData attributes as alternating key/value data.
    if not isinstance(attributes, dict) or not isinstance(attributes.get('data'), list):
        raise Rejected('unsupported event attributes')
    data = attributes['data']
    if len(data) % 2:
        raise Rejected('malformed event attributes')
    result = {}
    for index in range(0, len(data), 2):
        key = data[index].get('key') if isinstance(data[index], dict) else None
        if not isinstance(key, str) or key in result:
            raise Rejected('malformed or duplicate event attribute')
        result[key] = data[index + 1]
    return result


def verify_observation(invocation, spans, document, service):
    trace = invocation.get('traceId', '')
    if not re.fullmatch('[0-9a-f]{32}', trace) or int(trace, 16) == 0:
        raise Rejected('invalid trace ID')
    requests = invocation.get('requests', [])
    if len(requests) != 1:
        raise Rejected('expected one SDK request; retries/fan-out unsupported')
    request = requests[0]
    if not 100 <= request.get('status', 0) <= 599:
        raise Rejected('invalid HTTP status')
    if request.get('transportError') or request.get('hasQuery'):
        raise Rejected('transport error or nonempty options/query')
    prefix = f'/rest/{service}/v1.36.2'
    path = request['path']
    if not path.startswith(prefix + '/'):
        raise Rejected('unexpected mock prefix')
    path = path[len(prefix):]
    if not spans or any(span.get('traceId') != trace for span in spans):
        raise Rejected('missing or cross-trace evidence')
    matched = [span for span in spans if 'operation.name' in span.get('attributes', {})]
    if len(matched) != 1:
        raise Rejected(f'expected one operation span, found {len(matched)}')
    span = matched[0]
    invocations = [candidate for candidate in spans if any(event.get('name') == 'invocation_received' for event in candidate.get('events', []))]
    if len(invocations) != 1 or invocations[0] is not span:
        raise Rejected('ambiguous invocation evidence')
    if not span.get('spanId'):
        raise Rejected('missing span ID')
    attrs = span['attributes']
    template, operation = match_openapi(document, request['method'], path)
    if attrs.get('service.name') != service or attrs.get('service.version') != 'v1.36.2':
        raise Rejected('wrong service/version')
    if attrs.get('operation.method') != request['method'] or attrs.get('operation.name') != request['method'] + ' ' + template:
        raise Rejected('server operation disagrees with observed request/OpenAPI')
    events = [event for event in span.get('events', []) if event.get('name') == 'invocation_received']
    if len(events) != 1:
        raise Rejected('expected one invocation event')
    event = event_attributes(events[0]['attributes'])
    uri = urlsplit(event.get('uri.full', ''))
    if uri.path != request['path'] or uri.query or uri.fragment or event.get('http.method') != request['method'] or event.get('query.string') != 'empty':
        raise Rejected('server request disagrees with client request')
    # Response failure is intentionally separate from evidence of operation routing.
    return {
        'case': invocation['case'], 'sdkMethod': invocation['sdkMethod'],
        'traceId': trace, 'spanId': span['spanId'],
        'request': {'method': request['method'], 'path': path, 'status': request['status']},
        'serverOperation': attrs['operation.name'],
        'operationId': operation['operationId'],
        'kubernetesAction': operation.get('x-kubernetes-action'),
        'groupVersionKind': operation.get('x-kubernetes-group-version-kind'),
        'requestMatched': True, 'sdkSuccess': invocation['sdkSuccess'],
        'responseVerified': invocation['responseVerified'],
    }
