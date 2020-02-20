import os
import unittest

import complaints.ccdb.verify_s3 as sut
from common.tests import build_argv, captured_output, make_configargs

try:
    from unittest.mock import patch, Mock
except ImportError:
    from mock import patch, Mock


def toAbsolute(relative):
    # where is _this_ file?
    thisScriptDir = os.path.dirname(__file__)
    return os.path.join(thisScriptDir, relative)


# ------------------------------------------------------------------------------
# Classes
# ------------------------------------------------------------------------------


class TestMain(unittest.TestCase):
    def setUp(self):
        self.optional = [
            '--s3-bucket', 'foo',
            '--s3-folder', 'bar'
        ]

        self.json_size_file = toAbsolute('__fixtures__/prev_json_size.txt')
        self.cache_size_file = toAbsolute('__fixtures__/prev_cache_size.txt')

        self.positional = [
            'json_data.json',
            self.json_size_file,
            self.cache_size_file
        ]

    def tearDown(self):
        try:
            with open(self.json_size_file, 'w+') as f:
                f.write(str(0))
            with open(self.cache_size_file, 'w+') as f:
                f.write(str(0))
        except Exception:
            pass

    @patch('complaints.ccdb.verify_s3.boto3')
    def test_verify_happy_path(self, boto3):
        dataset = make_configargs({
            'content_length': 180
        })
        bucket = Mock()
        bucket.Object.return_value = dataset

        s3 = Mock()
        s3.Bucket.return_value = bucket
        boto3.resource.return_value = s3

        argv = build_argv(self.optional, self.positional)
        with captured_output(argv) as (out, err):
            sut.main()

        # assert calls
        boto3.resource.assert_called_once_with('s3')
        s3.Bucket.assert_called_once_with('foo')

        # assert file size update
        try:
            with open(self.json_size_file, 'r') as f:
                prev_json_size = int(f.read())
        except Exception:
            prev_json_size = 0

        self.assertTrue(prev_json_size == 180)

        # assert cache size update
        try:
            with open(self.cache_size_file, 'r') as f:
                prev_cache_size = int(f.read())
        except Exception:
            prev_cache_size = 0

        self.assertTrue(prev_cache_size != 0)

    @patch('complaints.ccdb.verify_s3.boto3')
    def test_verify_file_verify_failure(self, boto3):
        dataset = make_configargs({
            'content_length': -1
        })
        bucket = Mock()
        bucket.Object.return_value = dataset

        s3 = Mock()
        s3.Bucket.return_value = bucket
        boto3.resource.return_value = s3

        with self.assertRaises(SystemExit) as ex:
            argv = build_argv(self.optional, self.positional)
            with captured_output(argv) as (out, err):
                sut.main()

        # assert calls
        boto3.resource.assert_called_once_with('s3')
        s3.Bucket.assert_called_once_with('foo')

        # assert exit code
        self.assertEqual(ex.exception.code, 2)

    @patch('complaints.ccdb.verify_s3.boto3')
    def test_verify_cache_verify_failure(self, boto3):
        dataset = make_configargs({
            'content_length': 1
        })
        bucket = Mock()
        bucket.Object.return_value = dataset

        # set up intentionally large cache size
        with open(self.cache_size_file, 'w+') as f:
            f.write(str(99999999))

        s3 = Mock()
        s3.Bucket.return_value = bucket
        boto3.resource.return_value = s3

        with self.assertRaises(SystemExit) as ex:
            argv = build_argv(self.optional, self.positional)
            with captured_output(argv) as (out, err):
                sut.main()

        # assert calls
        boto3.resource.assert_called_once_with('s3')
        s3.Bucket.assert_called_once_with('foo')

        # assert exit code
        self.assertEqual(ex.exception.code, 2)
