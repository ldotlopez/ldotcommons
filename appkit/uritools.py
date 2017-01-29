import re
from urllib import parse


def is_sha1_urn(urn):
    """Check if urn matches sha1 urn: scheme
    """
    assert isinstance(urn, str)
    assert urn != ''

    return re.match('^urn:(.+?):[A-F0-9]{40}$', urn, re.IGNORECASE) is not None


def is_base32_urn(urn):
    """Check if urn matches base32 urn: scheme
    """
    assert isinstance(urn, str)
    assert urn != ''

    return re.match('^urn:(.+?):[A-Z2-7]{32}$', urn, re.IGNORECASE) is not None


def normalize(uri):
    assert isinstance(uri, str) and uri

    if '://' not in uri:
        uri = 'http://' + uri

    parsed = parse.urlparse(uri)
    path, dummy = re.subn(r'/+', '/', parsed.path or '/')
    parsed = parsed._replace(path=path)

    return parse.urlunparse(parsed)


def paginate_by_query_param(uri, key, default=1):
    """
    Utility generator for easy pagination
    """
    def alter_param(k, v):
        if k == key:
            try:
                v = int(v) + 1
            except ValueError:
                v = default

            v = str(v)

        return k, v

    yield uri

    parsed = parse.urlparse(uri)
    qsl = parse.parse_qsl(parsed.query)
    if key not in [x[0] for x in qsl]:
        qsl = qsl + [(key, default)]

    while True:
        qsl = [alter_param(*x) for x in qsl]
        yield parse.urlunparse((parsed.scheme, parsed.netloc, parsed.path,
                                parsed.params,
                                parse.urlencode(qsl, doseq=True),
                                parsed.fragment))
