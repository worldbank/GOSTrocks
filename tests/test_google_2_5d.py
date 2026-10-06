import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import pyproj
import numpy as np
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import MultiPolygon, Point, Polygon, box
from shapely.ops import transform

from GOSTrocks import dataMisc


class Google25DDownloadTests(unittest.TestCase):
    def setUp(self):
        self.region = box(47.50, -18.92, 47.51, -18.91)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.client = Mock()
        self.client_patch = patch.object(
            dataMisc.storage.Client, 'create_anonymous_client', return_value=self.client
        )
        self.client_patch.start()
        self.addCleanup(self.client_patch.stop)
        self.client.bucket.return_value.blob.return_value.download_to_filename.side_effect = (
            lambda filename: Path(filename).write_bytes(b'tile data')
        )
        source = {
            'affineTransform': {
                'scaleX': 0.01, 'scaleY': -0.01,
                'translateX': 47.49, 'translateY': -18.90,
            },
            'dimensions': {'width': 4, 'height': 4},
            'uris': ['height/tile.tif'],
        }
        distant_source = {
            **source,
            'affineTransform': {**source['affineTransform'], 'translateX': 10},
            'uris': ['height/distant.tif'],
        }
        self.manifest = {
            'uriPrefix': 'gs://open-buildings-temporal-data/v1/2023/',
            'tilesets': [{'crs': 'EPSG:4326', 'sources': [source, source, distant_source]}],
        }
        self.blob = Mock()
        self.blob.name = 'v1/manifests/token_2023_height.json'
        self.blob.download_as_bytes.side_effect = lambda: json.dumps(self.manifest).encode()
        old_blob = Mock()
        old_blob.name = 'v1/manifests/token_2022_height.json'
        self.client.list_blobs.return_value = [self.blob, old_blob]
        self.old_blob = old_blob

    def download(self, **kwargs):
        return dataMisc.download_google_2_5d(
            self.region, 2023, self.directory.name, **kwargs
        )

    def test_selects_year_and_intersection_and_deduplicates(self):
        paths = self.download()
        self.assertEqual(len(paths), 1)
        self.assertEqual(Path(paths[0]).read_bytes(), b'tile data')
        self.assertTrue(paths[0].endswith(str(Path('v1/2023/height/tile.tif'))))
        self.old_blob.download_as_bytes.assert_not_called()
        self.client.bucket.return_value.blob.assert_called_once_with('v1/2023/height/tile.tif')
        for call in self.client.list_blobs.call_args_list:
            self.assertTrue(call.kwargs['prefix'].startswith('v1/manifests/'))

    def test_existing_files_are_reused_and_overwrite_is_supported(self):
        self.download()
        self.download()
        self.assertEqual(self.client.bucket.return_value.blob.call_count, 1)
        self.download(overwrite=True)
        self.assertEqual(self.client.bucket.return_value.blob.call_count, 2)

    def test_projected_input(self):
        projection = pyproj.Transformer.from_crs(4326, 3857, always_xy=True)
        self.region = transform(projection.transform, self.region)
        self.assertEqual(len(self.download(crs='EPSG:3857')), 1)

    def test_live_style_uri_prefix(self):
        self.manifest['uriPrefix'] = 'gs://open-buildings-temporal-data/v1/geotiffs/2'
        for source in self.manifest['tilesets'][0]['sources']:
            source['uris'] = ['1d9c_2023_06_30/tile.tif']
        paths = self.download()
        self.assertEqual(len(paths), 1)
        self.client.bucket.return_value.blob.assert_called_once_with(
            'v1/geotiffs/21d9c_2023_06_30/tile.tif'
        )

    def test_multipolygon_input(self):
        self.region = MultiPolygon([self.region, box(47.52, -18.92, 47.525, -18.915)])
        self.assertEqual(len(self.download()), 1)

    def test_no_coverage_returns_empty_list(self):
        self.client.list_blobs.return_value = []
        self.assertEqual(self.download(), [])
        self.client.bucket.return_value.blob.assert_not_called()

    def write_test_tile(self, filename, left=0, value=1, crs='EPSG:4326'):
        with rasterio.open(
            filename, 'w', driver='GTiff', width=2, height=2, count=2,
            dtype='uint8', crs=crs, transform=from_origin(left, 2, 1, 1), nodata=0,
        ) as tile:
            tile.write(np.full((2, 2, 2), value, dtype='uint8'))

    def test_single_tile_vrt_preserves_pixels(self):
        self.client.bucket.return_value.blob.return_value.download_to_filename.side_effect = (
            self.write_test_tile
        )
        self.download(create_vrt=True)
        with rasterio.open(Path(self.directory.name) / 'google_2_5d.vrt') as vrt:
            self.assertEqual(vrt.driver, 'VRT')
            self.assertEqual(vrt.count, 2)
            np.testing.assert_array_equal(vrt.read(), np.ones((2, 2, 2), dtype='uint8'))

    def test_multiple_tile_vrt_mosaics_pixels(self):
        self.manifest['tilesets'][0]['sources'][1] = {
            **self.manifest['tilesets'][0]['sources'][0], 'uris': ['height/other.tif']
        }
        tile_number = iter([0, 1])

        def write_tile(filename):
            index = next(tile_number)
            self.write_test_tile(filename, left=index * 2, value=index + 1)

        self.client.bucket.return_value.blob.return_value.download_to_filename.side_effect = write_tile
        self.download(create_vrt=True)
        with rasterio.open(Path(self.directory.name) / 'google_2_5d.vrt') as vrt:
            self.assertEqual(vrt.shape, (2, 4))
            self.assertEqual(vrt.nodata, 0)
            np.testing.assert_array_equal(vrt.read(1), [[1, 1, 2, 2], [1, 1, 2, 2]])

    def test_no_coverage_does_not_create_vrt(self):
        self.client.list_blobs.return_value = []
        self.assertEqual(self.download(create_vrt=True), [])
        self.assertFalse((Path(self.directory.name) / 'google_2_5d.vrt').exists())

    def test_mixed_crs_is_rejected_without_creating_vrt(self):
        self.manifest['tilesets'][0]['sources'][1] = {
            **self.manifest['tilesets'][0]['sources'][0], 'uris': ['height/other.tif']
        }
        projections = iter(['EPSG:4326', 'EPSG:3857'])

        def write_tile(filename):
            self.write_test_tile(filename, crs=next(projections))

        self.client.bucket.return_value.blob.return_value.download_to_filename.side_effect = write_tile
        with self.assertRaisesRegex(ValueError, 'share a CRS'):
            self.download(create_vrt=True)
        self.assertFalse((Path(self.directory.name) / 'google_2_5d.vrt').exists())

    def test_failed_download_leaves_no_partial_file(self):
        self.client.bucket.return_value.blob.return_value.download_to_filename.side_effect = (
            RuntimeError('network failure')
        )
        with self.assertRaisesRegex(RuntimeError, 'network failure'):
            self.download()
        self.assertFalse(list(Path(self.directory.name).rglob('*.part')))
        self.assertFalse(list(Path(self.directory.name).rglob('*.tif')))

    def test_rejects_path_traversal(self):
        self.manifest['tilesets'][0]['sources'][0]['uris'] = ['../tile.tif']
        with self.assertRaisesRegex(ValueError, 'Unsafe tile path'):
            self.download()

    def test_invalid_inputs_fail_before_network_access(self):
        inputs = [
            (Point(0, 0), 2023, TypeError),
            (Polygon(), 2023, ValueError),
            (self.region, 2024, ValueError),
            (self.region, True, ValueError),
            (self.region, '2023', ValueError),
            (box(200, 0, 201, 1), 2023, ValueError),
        ]
        for region, year, error in inputs:
            with self.subTest(region=region, year=year):
                with self.assertRaises(error):
                    dataMisc.download_google_2_5d(region, year, self.directory.name)
        self.client.list_blobs.assert_not_called()


if __name__ == '__main__':
    unittest.main()