import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

from pipeline import dataset


class DatasetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()
        self.paths = patch.multiple(dataset, CACHE_DIR=self.root, DATASET_ZIP=self.root / "local.zip")
        self.paths.start()
        dataset.dataset_path.cache_clear()

    def tearDown(self):
        dataset.dataset_path.cache_clear()
        self.paths.stop()
        self.env.stop()
        self.temp.cleanup()

    def test_s3_unicode_key_and_disk_cache(self):
        def download(bucket, key, path):
            self.assertEqual((bucket, key), ("demo-20260912", "E_教育局-資料集.zip"))
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("資料集/測試.txt", "test")
        boto = Mock()
        boto.Session.return_value.client.return_value.download_file.side_effect = download
        with patch.dict("sys.modules", {"boto3": boto}):
            path = dataset.dataset_path()
            dataset.dataset_path.cache_clear()
            self.assertEqual(dataset.dataset_path(), path)
        boto.Session.return_value.client.return_value.download_file.assert_called_once()
        self.assertFalse(list(self.root.rglob("*.part")))

    def test_invalid_download_not_published(self):
        boto = Mock()
        boto.Session.return_value.client.return_value.download_file.side_effect = lambda b, k, p: Path(p).write_text("error")
        with patch.dict("sys.modules", {"boto3": boto}), self.assertRaises(ValueError):
            dataset.dataset_path()
        self.assertFalse(list(self.root.rglob("dataset.zip")))
        self.assertFalse(list(self.root.rglob("*.part")))

    def test_explicit_local_missing_does_not_fall_back(self):
        os.environ["DATASET_ZIP"] = str(self.root / "local.zip")
        with self.assertRaises(FileNotFoundError):
            dataset.dataset_path()

    def test_local_archive_without_aws(self):
        local = self.root / "local.zip"
        with zipfile.ZipFile(local, "w") as archive:
            archive.writestr("example", "test")
        self.assertEqual(dataset.dataset_path(), local)

    def test_invalid_uri(self):
        os.environ["DATASET_S3_URI"] = "https://example.com/archive.zip"
        with self.assertRaises(ValueError):
            dataset.dataset_path()


if __name__ == "__main__":
    unittest.main()
