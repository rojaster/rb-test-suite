# rb-test-suite
### Test-Suite for RedBaron

It was adopted with files from CPython Tests for `2.7` branch: https://github.com/python/cpython/tree/2.7/Lib/test
It is also related to the issue [#129](https://github.com/PyCQA/redbaron/issues/129) in `RedBaron`

The total amount of the tests comes to 486.
Tests for Python2.7 are being kept in `2.7` branch. 

Current results of running RedBaron over `test-suite`:

* Total count of the files: ***486***
* Succeed count of files: ***417***
* Failed count of files: ***69***


### Run tests from the command line
```bash
python -m pytest --ignore=./test-suite -lsv
```
> that's so important ignore `test-suite` directory, otherwise pytest collection stage will be collecting files from there

# About License
Since it has been related to the CPython repository, files from `test-suite` inherits their license policy.
And it's been using for testing purposes only.

