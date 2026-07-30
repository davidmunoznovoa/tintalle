import os
import tempfile
import unittest
import logging
from types import SimpleNamespace

from app import Main_Window


class TestNormalizeRawExtensions(unittest.TestCase):
    """The Anima requires sound file names to end in '.RAW' (case sensitive).

    normalize_raw_extensions() must return a list of paths whose file names
    all end in exactly '.RAW', without renaming the user's original files.
    See https://github.com/jramboz/tintalle/issues/42
    """

    def setUp(self):
        self.source_directory = tempfile.TemporaryDirectory()
        self.normalized_directory = tempfile.TemporaryDirectory()

        self.addCleanup(self.normalized_directory.cleanup)
        self.addCleanup(self.source_directory.cleanup)

        self.dir = self.source_directory.name

    def _normalize(self, files: list[str]) -> list[str]:
        return Main_Window.normalize_raw_extensions(
            files,
            self.normalized_directory.name,
        )

    def _make_file(self, name: str, content: bytes = b'\x00\x01') -> str:
        path = os.path.join(self.dir, name)
        with open(path, 'wb') as f:
            f.write(content)
        return path

    def test_lowercase_extension_is_uppercased(self):
        src = self._make_file('hum_0.raw', b'abc')
        result = self._normalize([src])
        self.assertEqual(len(result), 1)
        self.assertEqual(os.path.basename(result[0]), 'hum_0.RAW')

    def test_copy_has_same_content(self):
        src = self._make_file('hum_0.raw', b'abc')
        result = self._normalize([src])
        with open(result[0], 'rb') as f:
            self.assertEqual(f.read(), b'abc')

    def test_mixed_case_extension_is_uppercased(self):
        src = self._make_file('CLASH_1_0.Raw')
        result = self._normalize([src])
        self.assertEqual(os.path.basename(result[0]), 'CLASH_1_0.RAW')

    def test_correct_extension_returns_original_path(self):
        src = self._make_file('BEEP.RAW')
        result = self._normalize([src])
        self.assertEqual(result, [src])

    def test_original_file_is_not_renamed(self):
        src = self._make_file('swing.raw')
        self._normalize([src])
        self.assertTrue(os.path.exists(src))

    def test_non_raw_extension_left_untouched(self):
        src = self._make_file('readme.txt')
        result = self._normalize([src])
        self.assertEqual(result, [src])

    def test_order_is_preserved(self):
        a = self._make_file('a.raw')
        b = self._make_file('B.RAW')
        c = self._make_file('c.Raw')
        result = self._normalize([a, b, c])
        self.assertEqual([os.path.basename(p) for p in result],
                         ['a.RAW', 'B.RAW', 'c.RAW'])
        self.assertEqual(result[1], b)

    def test_normalized_files_share_temporary_directory(self):
        first = self._make_file('hum.raw')
        second = self._make_file('clash.Raw')

        result = self._normalize([first, second])

        self.assertEqual(
            {os.path.dirname(path) for path in result},
            {self.normalized_directory.name},
        )

class TestPrepareAndUploadFiles(unittest.IsolatedAsyncioTestCase):

    async def test_temporary_files_are_removed_after_upload(self):
        with tempfile.TemporaryDirectory() as source_directory:
            source = os.path.join(source_directory, 'hum.raw')

            with open(source, 'wb') as file:
                file.write(b'abc')

            uploaded_paths = []

            async def fake_upload(files):
                uploaded_paths.extend(files)

                # The temporary copy must still exist while uploading.
                self.assertTrue(os.path.exists(files[0]))
                self.assertEqual(
                    os.path.basename(files[0]),
                    'hum.RAW',
                )

            window = SimpleNamespace(
                normalize_raw_extensions=(
                    Main_Window.normalize_raw_extensions
                ),
                anima_is_NXT=lambda: False,
                files_dict={},
                log=logging.getLogger(),
                _upload_files=fake_upload,
            )

            await Main_Window._prepare_and_upload_files(
                window,
                [source],
            )

            # The upload has finished, so TemporaryDirectory must have
            # removed the normalized copy.
            self.assertFalse(os.path.exists(uploaded_paths[0]))

            # The user's original file remains untouched.
            self.assertTrue(os.path.exists(source))


if __name__ == '__main__':
    unittest.main()
