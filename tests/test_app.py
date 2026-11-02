from pathlib import Path

from prometheus_client import REGISTRY
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).parent.parent / "app.py")


def test_app_renders_without_error():
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    assert len(at.tabs) == 4
    assert len(at.slider) == 10


def test_predict_updates_metrics():
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.button[0].click().run()
    assert not at.exception
    assert at.success[0].value.startswith("Predicted genre:")
    assert REGISTRY.get_sample_value("prediction_latency_seconds_count") >= 1
