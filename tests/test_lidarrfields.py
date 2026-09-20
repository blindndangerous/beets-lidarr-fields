import unittest
from unittest import mock

from beetsplug.lidarrfields import LidarrFieldsPlugin


class FakeAlbum(object):
  def __init__(self, items):
    self._items = items

  def items(self):
    return self._items


class FakeItem(object):
  def __init__(self, item_id, album_id, artist, album, releasegroup_id='',
               album_id_external='', singleton=False, disc=1, disctotal=1,
               media='Digital Media'):
    self.id = item_id
    self.album_id = album_id
    self.albumartist = artist
    self.album = album
    self.mb_releasegroupid = releasegroup_id
    self.mb_albumid = album_id_external
    self.singleton = singleton
    self.disc = disc
    self.disctotal = disctotal
    self.media = media
    self._album = None

  def get_album(self):
    return self._album


class LidarrFieldsPluginTest(unittest.TestCase):
  def setUp(self):
    self.plugin = LidarrFieldsPlugin()

  @mock.patch('beetsplug.lidarrfields.musicbrainzngs.get_release_group_by_id')
  def test_missing_releasegroup_id_does_not_leak_artist(self, get_release_group):
    first = FakeItem(1, 10, 'Artist A', 'Album A')
    second = FakeItem(2, 11, 'Artist B', 'Album B')

    self.assertEqual(self.plugin._tmpl_releasegroupartist(first), 'Artist A')
    self.assertEqual(self.plugin._tmpl_releasegroupartist(second), 'Artist B')
    self.assertFalse(get_release_group.called)

  def test_missing_album_id_does_not_leak_title(self):
    first = FakeItem(1, 10, 'Artist A', 'First Album.')
    second = FakeItem(2, 11, 'Artist B', 'Second: Album?')

    self.assertEqual(self.plugin._tmpl_lidarralbum(first), 'First Album')
    self.assertEqual(self.plugin._tmpl_lidarralbum(second), 'Second- Album!')

  def test_missing_releasegroup_id_does_not_leak_disc_total(self):
    first = FakeItem(1, 10, 'Artist A', 'Album A', disc=1, disctotal=2)
    first_disc_two = FakeItem(2, 10, 'Artist A', 'Album A', disc=2,
                              disctotal=2)
    first._album = FakeAlbum([first, first_disc_two])

    second = FakeItem(3, 11, 'Artist B', 'Album B', disc=1, disctotal=3)
    second_disc_two = FakeItem(4, 11, 'Artist B', 'Album B', disc=2,
                               disctotal=3)
    second_disc_three = FakeItem(5, 11, 'Artist B', 'Album B', disc=3,
                                 disctotal=3)
    second._album = FakeAlbum([second, second_disc_two, second_disc_three])

    self.assertEqual(self.plugin._tmpl_audiodisctotal(first), '02')
    self.assertEqual(self.plugin._tmpl_audiodisctotal(second), '03')

  def test_singletons_use_separate_title_cache_entries(self):
    first = FakeItem(1, None, 'Artist A', 'First.', singleton=True)
    second = FakeItem(2, None, 'Artist B', 'Second?', singleton=True)

    self.assertEqual(self.plugin._tmpl_lidarralbum(first), 'First')
    self.assertEqual(self.plugin._tmpl_lidarralbum(second), 'Second!')


if __name__ == '__main__':
  unittest.main()
