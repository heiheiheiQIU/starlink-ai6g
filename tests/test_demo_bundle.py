"""A changed or missing payload must fail the portable offline integrity gate."""
import json
import hashlib
import pytest
from scripts.demo_acceptance import verify_integrity


def test_integrity_gate_detects_corruption_missing_and_unlisted_payload(tmp_path):
    (tmp_path/'start.py').write_bytes(b'print(1)')
    (tmp_path/'SHA256SUMS.json').write_text(json.dumps({'start.py':hashlib.sha256(b'print(1)').hexdigest()}),encoding='utf-8')
    assert verify_integrity(tmp_path) == 1
    (tmp_path/'start.py').write_bytes(b'print(2)')
    with pytest.raises(ValueError, match='hash'):
        verify_integrity(tmp_path)
    (tmp_path/'start.py').unlink()
    with pytest.raises(ValueError, match='missing'):
        verify_integrity(tmp_path)
    (tmp_path/'start.py').write_bytes(b'print(1)')
    (tmp_path/'injected.py').write_bytes(b'print(3)')
    with pytest.raises(ValueError, match='unlisted'):
        verify_integrity(tmp_path)
