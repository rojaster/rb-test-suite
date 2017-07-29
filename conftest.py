import pytest
import logging
import os

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)


class TSFilesReader(object):
    def __init__(self, test_suite_folder):
        self.__ts_files_list = [os.path.abspath(os.path.join(test_suite_folder, item))
                                for item in os.listdir(test_suite_folder)]

    @property
    def ts_files_list(self):
        return self.__ts_files_list

    def get_file_item(self):
        for file_item in self.ts_files_list:
            yield file_item

    def get_len_of_list(self):
        return len(self.ts_files_list)


@pytest.yield_fixture(scope="session", params=['test-suite'])
def ts_file_reader(request):
    """Read files absolute paths into a list from test-suite directory"""
    logger.info("Getting list of paths of the test suite files")
    yield TSFilesReader(request.param)
