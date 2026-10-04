"""Lidarr-compatible path fields with album-safe caching.

This locally overrides beets-lidarr-fields 1.1.2. The upstream plugin caches
values by external IDs. Empty or reused IDs can therefore leak values from one
album into another while paths are evaluated. Cache by the beets album ID
instead, which is the actual unit these fields describe.

The release-group artist is read from local tags rather than MusicBrainz.
Beets 2.x no longer sets a musicbrainzngs user agent, so every lookup failed
and folders silently fell back to the full credit ("Artist feat. Guest").
"""

import re
import unicodedata

from beets.plugins import BeetsPlugin

# A featured-artist suffix on a credit, e.g. "Gareth Emery feat. Krewella".
FEAT_RE = re.compile(r"\s+(?:feat\.?|ft\.?|featuring)\s.*$", re.IGNORECASE)


def _fold(name):
    """Compare artist names ignoring case and apostrophe style."""
    return (
        unicodedata.normalize("NFKC", name).replace("’", "'").casefold()
    )


VIDEO_MEDIA = {
    "Data CD",
    "DVD",
    "DVD-Video",
    "Blu-ray",
    "HD-DVD",
    "VCD",
    "SVCD",
    "UMD",
    "VHS",
}


class LidarrFieldsPlugin(BeetsPlugin):
    def __init__(self):
        super().__init__()
        self._release_group_artists = {}
        self._lidarr_albums = {}
        self._audio_disc_totals = {}
        self._canonical_names = None

        self.template_fields["releasegroupartist"] = (
            self._tmpl_releasegroupartist
        )
        self.template_fields["lidarralbum"] = self._tmpl_lidarralbum
        self.template_fields["audiodisctotal"] = self._tmpl_audiodisctotal

    @staticmethod
    def _album_key(item):
        """Return a per-album cache key, including unsaved album items."""
        if item.album_id is not None:
            return ("album", item.album_id)
        if item.id is not None:
            return ("item", item.id)
        return ("object", id(item))

    def _tmpl_releasegroupartist(self, item):
        if item.singleton:
            return None

        key = self._album_key(item)
        if key in self._release_group_artists:
            return self._release_group_artists[key]

        # The first credited artist, as Lidarr files it. albumartists holds
        # the canonical names; albums from other sources may leave it empty,
        # so fall back to the credit with any featured artist removed.
        names = item.albumartists
        artist = names[0] if names else FEAT_RE.sub("", item.albumartist)
        artist = self._canonical(item, artist)

        self._release_group_artists[key] = artist
        return artist

    def _canonical(self, item, name):
        """The spelling MusicBrainz-tagged albums use for this artist.

        Spotify, Discogs and Bandcamp spell some artists with different case
        or apostrophes ("Babymetal", "Blackmore's Night"), which would give
        the same artist a second folder.
        """
        if self._canonical_names is None:
            lib = getattr(item, "_db", None)
            if lib is None:
                return name
            self._canonical_names = {}
            for album in lib.albums("data_source:MusicBrainz"):
                names = album.albumartists or [album.albumartist]
                if names[0]:
                    self._canonical_names.setdefault(_fold(names[0]), names[0])
        return self._canonical_names.get(_fold(name), name)

    def _tmpl_lidarralbum(self, item):
        key = self._album_key(item)
        if key not in self._lidarr_albums:
            album = re.sub(r"\.$", "", item.album)
            self._lidarr_albums[key] = album.translate(
                str.maketrans({"/": "+", ":": "-", "?": "!"})
            )
        return self._lidarr_albums[key]

    def _tmpl_audiodisctotal(self, item):
        if item.singleton:
            return None

        key = self._album_key(item)
        if key in self._audio_disc_totals:
            return self._audio_disc_totals[key]

        discs = {
            album_item.disc
            for album_item in item.get_album().items()
            if album_item.media not in VIDEO_MEDIA
        }
        total = None if len(discs) <= 1 else str(len(discs)).zfill(2)
        self._audio_disc_totals[key] = total
        return total
