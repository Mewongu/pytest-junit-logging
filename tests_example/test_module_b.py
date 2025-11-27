import pytest


@pytest.fixture(scope='function')
def setup(logger):
    logger.info('Setting up')


@pytest.fixture(scope='function')
def teardown(logger):
    yield
    logger.info('Tearing down')


class TestClassB:
    @pytest.mark.parametrize('x', [True, False])
    def test_a(self, logger, x):
        logger.debug("Starting test_module_b.TestClassB.test_a")
        assert x, f'Expecting x to be True, Actual: {x=}'

