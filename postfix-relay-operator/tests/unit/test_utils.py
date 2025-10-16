# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.

import os
import shutil
import tempfile
import unittest
from pathlib import Path

import utils


class TestLibUtils(unittest.TestCase):
    def setUp(self):
        self.maxDiff = None
        self.tmpdir = tempfile.mkdtemp(prefix="charm-unittests-")
        self.charm_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        )
        self.addCleanup(shutil.rmtree, self.tmpdir)

    def test_logrotate_frequency(self):
        want = Path("tests/unit/files/logrotate_frequency").read_text(encoding="utf-8")
        got = utils.update_logrotate_conf("tests/unit/files/logrotate")
        self.assertEqual(got, want.strip())

    def test__write_file(self):
        source = "# User-provided config added here"
        dest = os.path.join(self.tmpdir, "my-test-file")

        utils.write_file(source, dest)

        with open(dest, "r") as f:
            got = f.read()
        self.assertEqual(got, source)
