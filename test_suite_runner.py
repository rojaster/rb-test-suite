import pytest
import logging
from redbaron import RedBaron
from io import open

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)


def test_rb_parser(ts_file_reader):
    """Check parsing by RedBaron agains files in test-sute"""
    succeed_files = []
    failed_files = []

    for f_path in ts_file_reader.get_file_item():
        try:
            with open(f_path, mode="r") as fh:
                RedBaron(fh.read())
            logger.info("Processing : {0} - OK".format(f_path))
            succeed_files.append(f_path)
        except:
            logger.info("Processing : {0} - FAILED".format(f_path))
            failed_files.append(f_path)

    logger.info("Total count of the files: {0}".format(ts_file_reader.get_len_of_list()))
    logger.info("Succeed count of files: {0}".format(len(succeed_files)))
    logger.info("Failed count of files: {0}".format(len(failed_files)))
