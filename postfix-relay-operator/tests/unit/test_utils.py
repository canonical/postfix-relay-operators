# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import os
import shutil
import tempfile
import unittest

import utils


class TestLibUtils(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.tmpdir = tempfile.mkdtemp(prefix="charm-unittests-")
        self.charm_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        )
        self.addCleanup(shutil.rmtree, self.tmpdir)

    def test__write_file(self):
        source = "# User-provided config added here"
        dest = os.path.join(self.tmpdir, "my-test-file")

        utils.write_file(source, dest)

        with open(dest, "r") as f:
            got = f.read()
        self.assertEqual(got, source)
