"""
Tests of regrtest.py.

Note: test_regrtest cannot be run twice in parallel.
"""
from __future__ import print_function

import collections
import errno
import os.path
import platform
import re
import subprocess
import sys
import sysconfig
import tempfile
import textwrap
import unittest
from test import support


Py_DEBUG = hasattr(sys, 'getobjects')
ROOT_DIR = os.path.join(os.path.dirname(__file__), '..', '..')
ROOT_DIR = os.path.abspath(os.path.normpath(ROOT_DIR))

TEST_INTERRUPTED = textwrap.dedent("""
    from signal import SIGINT
    try:
        from _testcapi import raise_signal
        raise_signal(SIGINT)
    except ImportError:
        import os
        os.kill(os.getpid(), SIGINT)
    """)


SubprocessRun = collections.namedtuple('SubprocessRun',
                                       'returncode stdout stderr')


class BaseTestCase(unittest.TestCase):
    TEST_UNIQUE_ID = 1
    TESTNAME_PREFIX = 'test_regrtest_'
    TESTNAME_REGEX = r'test_[a-zA-Z0-9_]+'

    def setUp(self):
        self.testdir = os.path.realpath(os.path.dirname(__file__))

        self.tmptestdir = tempfile.mkdtemp()
        self.addCleanup(support.rmtree, self.tmptestdir)

    def create_test(self, name=None, code=''):
        if not name:
            name = 'noop%s' % BaseTestCase.TEST_UNIQUE_ID
            BaseTestCase.TEST_UNIQUE_ID += 1

        # test_regrtest cannot be run twice in parallel because
        # of setUp() and create_test()
        name = self.TESTNAME_PREFIX + name
        path = os.path.join(self.tmptestdir, name + '.py')

        self.addCleanup(support.unlink, path)
        # Use O_EXCL to ensure that we do not override existing tests
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        except OSError as exc:
            if (exc.errno in (errno.EACCES, errno.EPERM)
               and not sysconfig.is_python_build()):
                self.skipTest("cannot write %s: %s" % (path, exc))
            else:
                raise
        else:
            with os.fdopen(fd, 'w') as fp:
                fp.write(code)
        return name

    def regex_search(self, regex, output):
        match = re.search(regex, output, re.MULTILINE)
        if not match:
            self.fail("%r not found in %r" % (regex, output))
        return match

    def check_line(self, output, regex):
        regex = re.compile(r'^' + regex, re.MULTILINE)
        self.assertRegexpMatches(output, regex)

    def parse_executed_tests(self, output):
        regex = (r'^[0-9]+:[0-9]+:[0-9]+ \[ *[0-9]+(?:/ *[0-9]+)*\] (%s)'
                 % self.TESTNAME_REGEX)
        parser = re.finditer(regex, output, re.MULTILINE)
        return list(match.group(1) for match in parser)

    def check_executed_tests(self, output, tests, skipped=(), failed=(),
                             omitted=(), randomize=False, interrupted=False):
        if isinstance(tests, str):
            tests = [tests]
        if isinstance(skipped, str):
            skipped = [skipped]
        if isinstance(failed, str):
            failed = [failed]
        if isinstance(omitted, str):
            omitted = [omitted]
        ntest = len(tests)
        nskipped = len(skipped)
        nfailed = len(failed)
        nomitted = len(omitted)

        executed = self.parse_executed_tests(output)
        if randomize:
            self.assertEqual(set(executed), set(tests), output)
        else:
            self.assertEqual(executed, tests, (executed, tests, output))

        def plural(count):
            return 's' if count != 1 else ''

        def list_regex(line_format, tests):
            count = len(tests)
            names = ' '.join(sorted(tests))
            regex = line_format % (count, plural(count))
            regex = r'%s:\n    %s$' % (regex, names)
            return regex

        if skipped:
            regex = list_regex('%s test%s skipped', skipped)
            self.check_line(output, regex)

        if failed:
            regex = list_regex('%s test%s failed', failed)
            self.check_line(output, regex)

        if omitted:
            regex = list_regex('%s test%s omitted', omitted)
            self.check_line(output, regex)

        good = ntest - nskipped - nfailed - nomitted
        if good:
            regex = r'%s test%s OK\.$' % (good, plural(good))
            if not skipped and not failed and good > 1:
                regex = 'All %s' % regex
            self.check_line(output, regex)

        if interrupted:
            self.check_line(output, 'Test suite interrupted by signal SIGINT.')

        if nfailed:
            result = 'FAILURE'
        elif interrupted:
            result = 'INTERRUPTED'
        else:
            result = 'SUCCESS'
        self.check_line(output, 'Tests result: %s' % result)

    def parse_random_seed(self, output):
        match = self.regex_search(r'Using random seed ([0-9]+)', output)
        randseed = int(match.group(1))
        self.assertTrue(0 <= randseed <= 10000000, randseed)
        return randseed

    def run_command(self, args, input=None, exitcode=0, **kw):
        if not input:
            input = ''
        if 'stderr' not in kw:
            kw['stderr'] = subprocess.PIPE
        proc = subprocess.Popen(args,
                                universal_newlines=True,
                                stdout=subprocess.PIPE,
                                **kw)
        stdout, stderr = proc.communicate(input=input)
        if proc.returncode != exitcode:
            msg = ("Command %s failed with exit code %s\n"
                   "\n"
                   "stdout:\n"
                   "---\n"
                   "%s\n"
                   "---\n"
                   % (str(args), proc.returncode, stdout))
            if proc.stderr:
                msg += ("\n"
                        "stderr:\n"
                        "---\n"
                        "%s"
                        "---\n"
                        % stderr)
            self.fail(msg)
        return SubprocessRun(proc.returncode, stdout, stderr)

    def run_python(self, args, **kw):
        args = [sys.executable] + list(args)
        proc = self.run_command(args, **kw)
        return proc.stdout


class ProgramsTestCase(BaseTestCase):
    """
    Test various ways to run the Python test suite. Use options close
    to options used on the buildbot.
    """

    NTEST = 4

    def setUp(self):
        super(ProgramsTestCase, self).setUp()

        # Create NTEST tests doing nothing
        self.tests = [self.create_test() for index in range(self.NTEST)]

        self.python_args = ['-Wd', '-3', '-E', '-bb', '-tt']
        self.regrtest_args = ['-uall', '-rwW',
                              '--testdir=%s' % self.tmptestdir]

    def check_output(self, output):
        self.parse_random_seed(output)
        self.check_executed_tests(output, self.tests, randomize=True)

    def run_tests(self, args):
        output = self.run_python(args)
        self.check_output(output)

    def test_script_regrtest(self):
        # Lib/test/regrtest.py
        script = os.path.join(self.testdir, 'regrtest.py')

        args = self.python_args + [script] + self.regrtest_args + self.tests
        self.run_tests(args)

    def test_module_test(self):
        # -m test
        args = self.python_args + ['-m', 'test'] + self.regrtest_args + self.tests
        self.run_tests(args)

    def test_module_regrtest(self):
        # -m test.regrtest
        args = self.python_args + ['-m', 'test.regrtest'] + self.regrtest_args + self.tests
        self.run_tests(args)

    def test_module_autotest(self):
        # -m test.autotest
        args = self.python_args + ['-m', 'test.autotest'] + self.regrtest_args + self.tests
        self.run_tests(args)

    def test_module_from_test_autotest(self):
        # from test import autotest
        code = 'from test import autotest'
        args = self.python_args + ['-c', code] + self.regrtest_args + self.tests
        self.run_tests(args)

    def test_script_autotest(self):
        # Lib/test/autotest.py
        script = os.path.join(self.testdir, 'autotest.py')
        args = self.python_args + [script] + self.regrtest_args + self.tests
        self.run_tests(args)

    def run_batch(self, *args):
        proc = self.run_command(args)
        self.check_output(proc.stdout)

    def need_pcbuild(self):
        exe = os.path.normpath(os.path.abspath(sys.executable))
        parts = exe.split(os.path.sep)
        if len(parts) < 3:
            # it's not a python build, python is likely to be installed
            return

        build_dir = parts[-3]
        if build_dir.lower() != 'pcbuild':
            self.skipTest("Tools/buildbot/test.bat requires PCbuild build, "
                          "found %s" % build_dir)

    @unittest.skipUnless(sysconfig.is_python_build(),
                         'test.bat script is not installed')
    @unittest.skipUnless(sys.platform == 'win32', 'Windows only')
    def test_tools_buildbot_test(self):
        self.need_pcbuild()

        # Tools\buildbot\test.bat
        script = os.path.join(ROOT_DIR, 'Tools', 'buildbot', 'test.bat')
        test_args = ['--testdir=%s' % self.tmptestdir]
        if platform.architecture()[0] == '64bit':
            test_args.append('-x64')   # 64-bit build
        if not Py_DEBUG:
            test_args.append('+d')     # Release build, use python.exe

        args = [script] + test_args + self.tests
        self.run_batch(*args)

    @unittest.skipUnless(sys.platform == 'win32', 'Windows only')
    def test_pcbuild_rt(self):
        self.need_pcbuild()

        # PCbuild\rt.bat
        script = os.path.join(ROOT_DIR, r'PCbuild\rt.bat')
        rt_args = ["-q"]             # Quick, don't run tests twice
        if platform.architecture()[0] == '64bit':
            rt_args.append('-x64')   # 64-bit build
        if Py_DEBUG:
            rt_args.append('-d')     # Debug build, use python_d.exe
        args = [script] + rt_args + self.regrtest_args + self.tests
        self.run_batch(*args)


class ArgsTestCase(BaseTestCase):
    """
    Test arguments of the Python test suite.
    """

    def run_tests(self, *testargs, **kw):
        cmdargs = ('-m', 'test', '--testdir=%s' % self.tmptestdir) + testargs
        return self.run_python(cmdargs, **kw)

    def test_failing_test(self):
        # test a failing test
        code = textwrap.dedent("""
            import unittest
            from test import support

            class FailingTest(unittest.TestCase):
                def test_failing(self):
                    self.fail("bug")

            def test_main():
                support.run_unittest(FailingTest)
        """)
        test_ok = self.create_test('ok')
        test_failing = self.create_test('failing', code=code)
        tests = [test_ok, test_failing]

        output = self.run_tests(*tests, exitcode=1)
        self.check_executed_tests(output, tests, failed=test_failing)

    def test_resources(self):
        # test -u command line option
        tests = {}
        for resource in ('audio', 'network'):
            code = 'from test import support\nsupport.requires(%r)' % resource
            tests[resource] = self.create_test(resource, code)
        test_names = sorted(tests.values())

        # -u all: 2 resources enabled
        output = self.run_tests('-u', 'all', *test_names)
        self.check_executed_tests(output, test_names)

        # -u audio: 1 resource enabled
        output = self.run_tests('-uaudio', *test_names)
        self.check_executed_tests(output, test_names,
                                  skipped=tests['network'])

        # no option: 0 resources enabled
        output = self.run_tests(*test_names)
        self.check_executed_tests(output, test_names,
                                  skipped=test_names)

    def test_random(self):
        # test -r and --randseed command line option
        code = textwrap.dedent("""
            import random
            print("TESTRANDOM: %s" % random.randint(1, 1000))
        """)
        test = self.create_test('random', code)

        # first run to get the output with the random seed
        output = self.run_tests('-r', '-v', test)
        randseed = self.parse_random_seed(output)
        match = self.regex_search(r'TESTRANDOM: ([0-9]+)', output)
        test_random = int(match.group(1))

        # try to reproduce with the random seed
        output = self.run_tests('-r', '-v', '--randseed=%s' % randseed, test)
        randseed2 = self.parse_random_seed(output)
        self.assertEqual(randseed2, randseed)

        match = self.regex_search(r'TESTRANDOM: ([0-9]+)', output)
        test_random2 = int(match.group(1))
        self.assertEqual(test_random2, test_random)

    def test_fromfile(self):
        # test --fromfile
        tests = [self.create_test() for index in range(5)]

        # Write the list of files using a format similar to regrtest output:
        # [1/2] test_1
        # [2/2] test_2
        filename = support.TESTFN
        self.addCleanup(support.unlink, filename)

        # test format 'test_opcodes'
        with open(filename, "w") as fp:
            for name in tests:
                print(name, file=fp)

        output = self.run_tests('--fromfile', filename)
        self.check_executed_tests(output, tests)

    def test_interrupted(self):
        code = TEST_INTERRUPTED
        test = self.create_test('sigint', code=code)
        output = self.run_tests(test, exitcode=1)
        self.check_executed_tests(output, test, omitted=test,
                                  interrupted=True)

    def test_slowest(self):
        # test --slow
        tests = [self.create_test() for index in range(3)]
        output = self.run_tests("--slowest", *tests)
        self.check_executed_tests(output, tests)
        regex = ('10 slowest tests:\n'
                 '(?:- %s: .*\n){%s}'
                 % (self.TESTNAME_REGEX, len(tests)))
        self.check_line(output, regex)

    def test_slow_interrupted(self):
        # Issue #25373: test --slowest with an interrupted test
        code = TEST_INTERRUPTED
        test = self.create_test("sigint", code=code)

        try:
            import threading
            tests = (False, True)
        except ImportError:
            tests = (False,)
        for multiprocessing in tests:
            if multiprocessing:
                args = ("--slowest", "-j2", test)
            else:
                args = ("--slowest", test)
            output = self.run_tests(*args, exitcode=1)
            self.check_executed_tests(output, test,
                                      omitted=test, interrupted=True)

            regex = ('10 slowest tests:\n')
            self.check_line(output, regex)

    def test_coverage(self):
        # test --coverage
        test = self.create_test('coverage')
        output = self.run_tests("--coverage", test)
        self.check_executed_tests(output, [test])
        regex = (r'lines +cov% +module +\(path\)\n'
                 r'(?: *[0-9]+ *[0-9]{1,2}% *[^ ]+ +\([^)]+\)+)+')
        self.check_line(output, regex)

    def test_forever(self):
        # test --forever
        code = textwrap.dedent("""
            import __builtin__
            import unittest
            from test import support

            class ForeverTester(unittest.TestCase):
                def test_run(self):
                    # Store the state in the __builtin__ module, because the test
                    # module is reload at each run
                    if 'RUN' in __builtin__.__dict__:
                        __builtin__.__dict__['RUN'] += 1
                        if __builtin__.__dict__['RUN'] >= 3:
                            self.fail("fail at the 3rd runs")
                    else:
                        __builtin__.__dict__['RUN'] = 1

            def test_main():
                support.run_unittest(ForeverTester)
        """)
        test = self.create_test('forever', code=code)
        output = self.run_tests('--forever', test, exitcode=1)
        self.check_executed_tests(output, [test]*3, failed=test)

    def test_list_tests(self):
        # test --list-tests
        tests = [self.create_test() for i in range(5)]
        output = self.run_tests('--list-tests', *tests)
        self.assertEqual(output.rstrip().splitlines(),
                         tests)

    def test_crashed(self):
        # Any code which causes a crash
        code = 'import ctypes; ctypes.string_at(0)'
        crash_test = self.create_test(name="crash", code=code)
        ok_test = self.create_test(name="ok")

        tests = [crash_test, ok_test]
        output = self.run_tests("-j2", *tests, exitcode=1)
        self.check_executed_tests(output, tests, failed=crash_test,
                                  randomize=True)

    def parse_methods(self, output):
        regex = re.compile("^(test[^ ]+).*ok$", flags=re.MULTILINE)
        return [match.group(1) for match in regex.finditer(output)]

    def test_matchfile(self):
        # Any code which causes a crash
        code = textwrap.dedent("""
            import unittest
            from test import support

            class Tests(unittest.TestCase):
                def test_method1(self):
                    pass
                def test_method2(self):
                    pass
                def test_method3(self):
                    pass
                def test_method4(self):
                    pass

            def test_main():
                support.run_unittest(Tests)
        """)
        all_methods = ['test_method1', 'test_method2',
                       'test_method3', 'test_method4']
        testname = self.create_test(code=code)

        # by default, all methods should be run
        output = self.run_tests("-v", testname)
        methods = self.parse_methods(output)
        self.assertEqual(methods, all_methods)

        # only run a subset
        filename = support.TESTFN
        self.addCleanup(support.unlink, filename)

        subset = [
            # only match the method name
            'test_method1',
            # match the full identifier
            '%s.Tests.test_method3' % testname]
        with open(filename, "w") as fp:
            for name in subset:
                print(name, file=fp)

        output = self.run_tests("-v", "--matchfile", filename, testname)
        methods = self.parse_methods(output)
        subset = ['test_method1', 'test_method3']
        self.assertEqual(methods, subset)

    def test_list_cases(self):
        # test --list-cases
        code = textwrap.dedent("""
            import unittest
            from test import support

            class Tests(unittest.TestCase):
                def test_method1(self):
                    pass
                def test_method2(self):
                    pass

            def test_main():
                support.run_unittest(Tests)
        """)
        testname = self.create_test(code=code)
        all_methods = ['%s.Tests.test_method1' % testname,
                       '%s.Tests.test_method2' % testname]
        output = self.run_tests('--list-cases', testname)
        self.assertEqual(output.splitlines(), all_methods)


def test_main():
    support.run_unittest(ProgramsTestCase, ArgsTestCase)


if __name__ == "__main__":
    test_main()
