

class TestClassA:
    def test_a(self, logger):
        logger.debug("Starting test_module_a.TestClassA.test_a")
        assert True
    def test_b(self, logger):
        logger.debug("Starting test_module_a.TestClassA.test_b")
        assert True

