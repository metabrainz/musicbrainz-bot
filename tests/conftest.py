import pytest
import tests.utils as utils


@pytest.fixture(scope="session", autouse=True)
def reset_db():
    return utils.reset_db()
