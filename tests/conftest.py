import copy

import pytest

from listing_auditor import load_config
from listing_auditor.sources.synthetic import generate


@pytest.fixture(scope="session")
def config():
    return load_config()


@pytest.fixture(scope="session")
def portfolio():
    rows, injected = generate(count=250, seed=11, defect_rate=0.5)
    return rows, injected


@pytest.fixture
def clean(portfolio):
    """A deep copy of one listing that has no planted defects."""
    rows, injected = portfolio
    row = next(r for r in rows if r["id"] not in injected)
    return copy.deepcopy(row)
