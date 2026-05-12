from sseint.export import status_code


def test_http11_status_line():
    assert status_code("HTTP/1.1 200 OK") == 200


def test_h2_has_no_status_line():
    assert status_code("200 OK") == 200


def test_error_status():
    assert status_code("HTTP/1.1 503 Service Unavailable") == 503


def test_version_number_is_not_mistaken_for_a_status():
    assert status_code("HTTP/2 204 No Content") == 204


def test_nothing_usable():
    assert status_code("") == 0
    assert status_code("weird") == 0
