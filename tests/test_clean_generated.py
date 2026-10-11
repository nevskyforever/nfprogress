"""Safety checks for explicit generated-output cleanup, using disposable repos."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/maintenance/clean_generated.py'
spec = importlib.util.spec_from_file_location('clean_generated', SCRIPT)
clean = importlib.util.module_from_spec(spec)
spec.loader.exec_module(clean)


class CleanupSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        (self.root / '.gitignore').write_text('frontend/src-tauri/target/\nfrontend/dist/\n')
        self.target = self.root / 'frontend/src-tauri/target'
        self.target.mkdir(parents=True)
        (self.target / 'object.o').write_bytes(b'generated')

    def track(self, path):
        subprocess.run(['git', '-C', str(self.root), 'add', '-f', path], check=True)

    def test_default_retains_outputs_apply_removes_only_allowlisted(self):
        source = self.root / 'frontend/src-tauri/Cargo.lock'
        source.write_text('lockfile')
        protected = self.root / '__pycache__/engine.cpython-312.pyc'
        protected.parent.mkdir()
        protected.write_bytes(b'protected')
        with patch.object(clean, 'repository_root', return_value=self.root), patch.object(clean, 'worktree_report'), patch.object(sys, 'argv', ['clean_generated.py']):
            self.assertEqual(clean.main(), 0)
        self.assertTrue(self.target.exists())
        with patch.object(clean, 'repository_root', return_value=self.root), patch.object(clean, 'worktree_report'), patch.object(sys, 'argv', ['clean_generated.py', '--apply']):
            self.assertEqual(clean.main(), 0)
        self.assertFalse(self.target.exists())
        self.assertEqual(source.read_text(), 'lockfile')
        self.assertEqual(protected.read_bytes(), b'protected')

    def test_tracked_output_blocks_whole_apply(self):
        dist = self.root / 'frontend/dist'
        dist.mkdir()
        (dist / 'user.txt').write_text('keep')
        self.track('frontend/dist/user.txt')
        with patch.object(clean, 'repository_root', return_value=self.root), patch.object(clean, 'worktree_report'), patch.object(sys, 'argv', ['clean_generated.py', '--apply']):
            self.assertEqual(clean.main(), 1)
        self.assertTrue((self.target / 'object.o').exists())
        self.assertTrue((dist / 'user.txt').exists())

    def test_unignored_output_refused(self):
        (self.root / '.gitignore').write_text('')
        with self.assertRaisesRegex(ValueError, 'not ignored'):
            clean.validate(self.root, 'frontend/src-tauri/target')

    def test_unallowlisted_and_tracked_ancestor_refused(self):
        with self.assertRaisesRegex(ValueError, 'Not allowlisted'):
            clean.validate(self.root, '../outside')
        self.track('frontend/src-tauri/target/object.o')
        with self.assertRaisesRegex(ValueError, 'Tracked content'):
            clean.validate(self.root, 'frontend/src-tauri/target')

    def test_symlinks_escaping_root_and_internal_alias_refused(self):
        with tempfile.TemporaryDirectory() as outside:
            (self.target / 'link').symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'Symlink escapes'):
                clean.validate(self.root, 'frontend/src-tauri/target')
            (self.target / 'link').unlink()
            (self.root / 'frontend/dist').symlink_to(self.target, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'Symlinked'):
                clean.validate(self.root, 'frontend/dist')

    def test_protected_content_and_nested_git_refused(self):
        for name in ('engine.cpython-312.pyc', '__pycache__', '.git'):
            entry = self.target / name
            entry.write_text('keep')
            with self.assertRaisesRegex(ValueError, 'Protected/nested'):
                clean.validate(self.root, 'frontend/src-tauri/target')
            entry.unlink()

    def test_size_does_not_follow_links_or_double_count_hardlinks(self):
        import os
        os.link(self.target / 'object.o', self.target / 'hardlink.o')
        (self.target / 'symlink.o').symlink_to(self.target / 'object.o')
        self.assertEqual(clean.size(self.target)[0], len(b'generated'))


if __name__ == '__main__':
    unittest.main()
