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

# Guests on a credit file under the main act: "A feat. B", "A with B",
# "A presents B" all belong to A.
GUEST_RE = re.compile(r"\s+(?:feat\.?|ft\.?|featuring|with|presents)\s.*$", re.IGNORECASE)

# Curly quotes and the Unicode hyphen fold to their plain ASCII forms.
_FOLD = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "‐": "-"})


def _fold(name):
    """Compare artist names ignoring case and quote or hyphen style."""
    return unicodedata.normalize("NFKC", name).translate(_FOLD).casefold()


def _credited(credit, names):
    """The artists of `names` still in `credit` once guests are removed, in order."""
    main = _fold(GUEST_RE.sub("", credit or ""))
    return [name for name in names if name and _fold(name) in main]


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
        self._names = None
        self._credits = None

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
        """The artist folder: who the album is credited to, minus guests.

        A solo album files under its artist; a collaboration ("Apollo Brown
        & Locksmith") gets its own folder named after the credit.
        """
        if item.singleton:
            return None

        key = self._album_key(item)
        if key not in self._release_group_artists:
            credit = GUEST_RE.sub("", item.albumartist or "").strip()
            names = _credited(item.albumartist, item.albumartists or []) or [credit]
            self._release_group_artists[key] = self._folder_name(item, credit, names)
        return self._release_group_artists[key]

    def _folder_name(self, item, credit, names):
        """Spell the folder the way MusicBrainz-tagged albums do.

        Spotify, Discogs and Bandcamp spell some artists differently
        ("Babymetal", '"Weird Al"' with straight quotes) and join
        collaborations differently ("AK, Sublab", "A + B"), which would give
        the same act a second folder.  A collaboration MusicBrainz has never
        credited is joined with " & ".
        """
        if not self._load_spellings(item):
            return credit
        if len(names) == 1:
            return self._names.get(_fold(names[0]), names[0])
        known = self._credits.get(tuple(_fold(name) for name in names))
        return known or " & ".join(self._names.get(_fold(name), name) for name in names)

    def _load_spellings(self, item):
        """Read every MusicBrainz album's artist spellings once per run."""
        if self._names is not None:
            return True
        lib = getattr(item, "_db", None)
        if lib is None:
            return False
        self._names, self._credits = {}, {}
        for album in lib.albums("data_source:MusicBrainz"):
            names = _credited(album.albumartist, album.albumartists or []) or [album.albumartist]
            for name in names:
                if name:
                    self._names.setdefault(_fold(name), name)
            if len(names) > 1:
                credit = GUEST_RE.sub("", album.albumartist).strip()
                self._credits.setdefault(tuple(_fold(name) for name in names), credit)
        return True

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
