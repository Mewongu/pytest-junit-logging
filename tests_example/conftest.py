import logging

import pytest


@pytest.fixture(scope='session')
def logger():
    # Should provide a new logger for each parametrized test case
    return logging.getLogger(__name__)

@pytest.fixture(scope='session')
def session_fixture(logger):
    logger.info('Session fixture initializing')
    yield
    logger.info('Session fixture terminating')

@pytest.fixture(scope='function')
def function_fixture(logger):
    logger.info('Function fixture initializing')
    yield
    logger.info('Function fixture terminating')

@pytest.fixture(scope="module")
def module_fixture(logger):
    logger.info('Module fixture initializing')
    yield
    logger.info('Module fixture terminating')