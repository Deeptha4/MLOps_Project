import pytest

import train


@pytest.fixture(scope="session", autouse=True)
def trained_artifacts():
    """Train once so tests always run against fresh artifacts."""
    return train.main()
