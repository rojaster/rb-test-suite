# -*- coding: utf-8 -*-
# Creation Date : 29/07/2017
# Author: alekum
#
# Smoke Parsing test for baron and redbaron libraries

# system imports
import pytest
import logging
from io import open

# baron and redbaron imports
from baron import parse
from redbaron import RedBaron

# logging?
logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(level=logging.DEBUG)


def _parsing_files(parse_func, files_provider, results_store):
    for f_path in files_provider.get_file_item():
        try:
            with open(f_path, mode="r") as fh:
                parse_func(fh.read())
            logger.info("Processing : {1} : {0} - OK".format(f_path, parse_func))
            results_store.add_succeed(f_path)
        except Exception as e:
            logger.info("Processing : {2} : {0} - FAILED - {1}".format(f_path, e.message, parse_func))
            results_store.add_failed(f_path)

    logger.info("Total count of the files: {0}".format(files_provider.get_len_of_list()))
    logger.info("Succeed count of files: {0}".format(results_store.count_of_succeed_tests()))
    logger.info("Failed count of files: {0}".format(results_store.count_of_failed_tests()))


# Mixed parametrized test
@pytest.mark.parametrize("parser_func", [RedBaron, parse])
def test_parsing(ts_provider, ts_results, parser_func):
    _parsing_files(parser_func, ts_provider, ts_results)
