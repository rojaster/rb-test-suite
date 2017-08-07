import pytest
import logging
from redbaron import RedBaron
from io import open
from baron import parse


logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)


def test_rb_parser(ts_reader, ts_results):
    """Check parsing by RedBaron against files in test-sute"""

    for f_path in ts_reader.get_file_item():
        try:
            with open(f_path, mode="r") as fh:
                RedBaron(fh.read())
            logger.info("Processing : {0} - OK".format(f_path))
            ts_results.add_succeed(f_path)
        except Exception as e:
            logger.info("Processing : {0} - FAILED - {1}".format(f_path, e.message))
            ts_results.add_failed(f_path)

    logger.info("Total count of the files: {0}".format(ts_reader.get_len_of_list()))
    logger.info("Succeed count of files: {0}".format(ts_results.count_of_succeed_tests()))
    logger.info("Failed count of files: {0}".format(ts_results.count_of_failed_tests()))


def test_baron_parser(ts_reader, ts_results):
    """Check parsing by baron against files in test-sute"""

    for f_path in ts_reader.get_file_item():
        try:
            with open(f_path, mode="r") as fh:
                parse(fh.read())
            logger.info("Processing : {0} - OK".format(f_path))
            ts_results.add_succeed(f_path)
        except Exception as e:
            logger.info("Processing : {0} - FAILED - {1}".format(f_path, e.message))
            ts_results.add_failed(f_path)

    logger.info("Total count of the files: {0}".format(ts_reader.get_len_of_list()))
    logger.info("Succeed count of files: {0}".format(ts_results.count_of_succeed_tests()))
    logger.info("Failed count of files: {0}".format(ts_results.count_of_failed_tests()))
