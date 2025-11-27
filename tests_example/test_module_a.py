

class TestClassA:
    def test_a(self, logger, session_fixture, module_fixture, function_fixture):
        logger.debug("Starting test_module_a.TestClassA.test_a")
        assert True
    def test_b(self, logger, session_fixture, module_fixture, function_fixture):
        logger.debug("Starting test_module_a.TestClassA.test_b")
        assert True

