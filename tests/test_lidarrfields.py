import unittest

from beetsplug.lidarrfields import LidarrFieldsPlugin


class FakeAlbum(object):
  def __init__(self, items):
    self._items = items

  def items(self):
    return self._items


class FakeItem(object):
  def __init__(self, item_id, album_id, artist, album, releasegroup_id='',
               album_id_external='', singleton=False, disc=1, disctotal=1,
               media='Digital Media', albumartists=None, db=None):
    self.id = item_id
    self.album_id = album_id
    self.albumartist = artist
    self.albumartists = albumartists or []
    self._db = db
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


class FakeLibraryAlbum(object):
  def __init__(self, artist, artists=None):
    self.albumartist = artist
    self.albumartists = artists or [artist]


class FakeLibrary(object):
  def __init__(self, albums):
    self._albums = albums

  def albums(self, query):
    assert query == 'data_source:MusicBrainz'
    return self._albums


class LidarrFieldsPluginTest(unittest.TestCase):
  def setUp(self):
    self.plugin = LidarrFieldsPlugin()

  def test_missing_releasegroup_id_does_not_leak_artist(self):
    first = FakeItem(1, 10, 'Artist A', 'Album A')
    second = FakeItem(2, 11, 'Artist B', 'Album B')

    self.assertEqual(self.plugin._tmpl_releasegroupartist(first), 'Artist A')
    self.assertEqual(self.plugin._tmpl_releasegroupartist(second), 'Artist B')

  def test_featured_artists_file_under_the_first_artist(self):
    tagged = FakeItem(1, 10, 'Gareth Emery feat. Krewella', 'A',
                      albumartists=['Gareth Emery', 'Krewella'])
    untagged = FakeItem(2, 11, 'Lost Frequencies ft. Axel Ehnstr\u00f6m', 'B')

    self.assertEqual(self.plugin._tmpl_releasegroupartist(tagged),
                     'Gareth Emery')
    self.assertEqual(self.plugin._tmpl_releasegroupartist(untagged),
                     'Lost Frequencies')

  def test_other_sources_take_the_musicbrainz_spelling(self):
    db = FakeLibrary([FakeLibraryAlbum("Blackmore\u2019s Night"),
                      FakeLibraryAlbum('BABYMETAL')])
    apostrophe = FakeItem(1, 10, "Blackmore's Night", 'A', db=db)
    case = FakeItem(2, 11, 'Babymetal', 'B', albumartists=['Babymetal'], db=db)

    self.assertEqual(self.plugin._tmpl_releasegroupartist(apostrophe),
                     'Blackmore\u2019s Night')
    self.assertEqual(self.plugin._tmpl_releasegroupartist(case), 'BABYMETAL')

  def test_collaborations_keep_their_own_folder(self):
    item = FakeItem(1, 10, 'Apollo Brown & Locksmith', 'No Question',
                    albumartists=['Apollo Brown', 'Locksmith'])
    guest = FakeItem(2, 11, 'Above & Beyond presents OceanLab', 'B',
                     albumartists=['Above & Beyond', 'OceanLab'])

    self.assertEqual(self.plugin._tmpl_releasegroupartist(item),
                     'Apollo Brown & Locksmith')
    self.assertEqual(self.plugin._tmpl_releasegroupartist(guest),
                     'Above & Beyond')

  def test_other_sources_join_a_collaboration_like_musicbrainz(self):
    db = FakeLibrary([
        FakeLibraryAlbum('Tom MacDonald & Nova Rockafeller',
                         ['Tom MacDonald', 'Nova Rockafeller']),
        FakeLibraryAlbum('“Weird Al” Yankovic'),
    ])
    plus = FakeItem(1, 10, 'Tom MacDonald + Nova Rockafeller', 'A',
                    albumartists=['Tom MacDonald', 'Nova Rockafeller'], db=db)
    unknown = FakeItem(2, 11, 'AK, Sublab', 'B',
                       albumartists=['AK', 'Sublab'], db=db)
    quotes = FakeItem(3, 12, '"Weird Al" Yankovic', 'C', db=db)

    self.assertEqual(self.plugin._tmpl_releasegroupartist(plus),
                     'Tom MacDonald & Nova Rockafeller')
    self.assertEqual(self.plugin._tmpl_releasegroupartist(unknown), 'AK & Sublab')
    self.assertEqual(self.plugin._tmpl_releasegroupartist(quotes),
                     '“Weird Al” Yankovic')

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
