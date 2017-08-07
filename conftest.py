import pytest
import logging
import os
import fnmatch

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)


class TSFilesReader(object):
    def __init__(self, test_suite_folder):
        self.__ts_files_list = [os.path.abspath(os.path.join(test_suite_folder, item))
                                for item in os.listdir(test_suite_folder) if fnmatch.fnmatch(item, '*.py')]

    @property
    def ts_files_list(self):
        return self.__ts_files_list

    def get_file_item(self):
        for file_item in self.ts_files_list:
            yield file_item

    def get_len_of_list(self):
        return len(self.ts_files_list)


class TSTestsResults(object):
    def __init__(self):
        self.__succeed_tests = list()
        self.__failed_tests = list()

    @property
    def succeed_tests(self):
        return self.__succeed_tests

    @property
    def faield_tests(self):
        return self.__failed_tests

    def add_succeed(self, test_file):
        self.__succeed_tests.append(test_file)
        return self

    def add_failed(self, test_file):
        self.__failed_tests.append(test_file)
        return self

    def count_of_succeed_tests(self):
        return len(self.__succeed_tests)

    def count_of_failed_tests(self):
        return len(self.__failed_tests)


@pytest.yield_fixture(scope="session", params=['test-suite'])
def ts_provider(request):
    """Read files absolute paths into a list from test-suite directory"""
    logger.info("Getting list of paths of the test suite files")
    yield TSFilesReader(request.param)

@pytest.yield_fixture(scope="function")
def ts_results():
    """Initializing TS test results store"""
    logger.info("Initializing TS test results store")
    yield TSTestsResults()
