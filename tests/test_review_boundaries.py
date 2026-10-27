"""Independent merge-review regressions for malformed window metadata."""
import numpy as np
import pytest
from backend.health.legacy_adapter import FEATURE_ORDER, HealthInputError, predict_npz_windows
from training.legacy_audit import AuditError, inspect_npz


def valid_fields():
    return dict(X=np.zeros((2,15,11), dtype=np.float32), y=np.zeros(2), y_fraction=np.zeros(2),
                run_id=np.array(['r','r']), time_index=np.array([0,3]), feature_names=np.array(FEATURE_ORDER),
                window_size=np.array(15), stride=np.array(3), step_unit=np.array('cycle'), rul_unit=np.array('cycles'))


@pytest.mark.parametrize('change', [
    {'y': np.zeros(1)}, {'y_fraction': np.zeros((2,1))}, {'run_id': np.array(['r'])},
    {'X': np.zeros((2,15,1))}, {'stride': np.array(-3)}, {'window_size': np.array(15.5)},
    {'time_index': np.array([0.9,3])}, {'time_index': np.array([-1,3])},
    {'step_unit': np.array('unknown')}, {'rul_unit': np.array('orbits')},
])
def test_audit_rejects_inconsistent_schema(tmp_path, change):
    fields=valid_fields(); fields.update(change)
    path=tmp_path/'bad.npz'; np.savez(path, **fields)
    with pytest.raises(AuditError):
        inspect_npz(path)


@pytest.mark.parametrize('change', [
    {'time_index': np.array([0.9,3])}, {'time_index': np.array([-1,3])},
    {'time_index': np.array([[0],[3]])}, {'step_unit': np.array('unknown')},
])
def test_adapter_rejects_bad_metadata_before_checkpoint(tmp_path, change):
    fields=valid_fields(); fields.update(change)
    path=tmp_path/'bad.npz'; np.savez(path, **fields)
    with pytest.raises(HealthInputError):
        predict_npz_windows(path, tmp_path/'missing.pt', 'lstm', [0], now_index=14)
