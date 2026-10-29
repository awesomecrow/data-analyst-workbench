import os
import pytest
from workbench.doctor import check_python_pkg, check_command
from workbench.checkpoint import CheckpointTracker


def test_doctor_checks():
    """Verify core analytical packages and system commands can be detected."""
    ok_duckdb, _ = check_python_pkg("duckdb")
    ok_polars, _ = check_python_pkg("polars")
    ok_pandas, _ = check_python_pkg("pandas")
    
    assert ok_duckdb is True
    assert ok_polars is True
    assert ok_pandas is True


def test_checkpoint_tracker(tmp_path, monkeypatch):
    """Verify CheckpointTracker records stages and quarantine error log."""
    monkeypatch.chdir(tmp_path)
    
    tracker = CheckpointTracker(project_name="unit-test-pipeline")
    tracker.record_stage(
        stage_num=1,
        stage_name="EXTRACT",
        what="Extracted test records",
        why="Validate unit testing",
        how="In-memory assertion",
        status="PASSED",
        metrics={"rows": 100}
    )
    
    tracker.log_quarantine(
        gate="SOURCE_VALIDATION",
        source_table="test_table",
        reason="Negative amount",
        rejected_count=2,
        sample_records=[{"id": 1, "amt": -10}]
    )
    
    manifest_path = tracker.finalize("SUCCESS")
    
    assert os.path.exists(manifest_path)
    assert os.path.exists("data/quarantine/error_log.json")
    assert tracker.overall_status == "SUCCESS"
    assert len(tracker.stages) == 1
    assert len(tracker.quarantine_entries) == 1
