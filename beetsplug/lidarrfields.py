from beets.plugins import BeetsPlugin
import musicbrainzngs
import re

class LidarrFieldsPlugin(BeetsPlugin):
  def __init__(self):
    super(LidarrFieldsPlugin, self).__init__()
    
    self.releasegroupartists = {}
    self.lidarralbums = {}
    self.audiodisctotals = {}
    
    self.template_fields['releasegroupartist'] = self._tmpl_releasegroupartist
    self.template_fields['lidarralbum'] = self._tmpl_lidarralbum
    self.template_fields['audiodisctotal'] = self._tmpl_audiodisctotal

  @staticmethod
  def _album_key(item):
    """Return a stable cache key for albums and singleton items."""
    if item.album_id is not None:
      return ('album', item.album_id)
    if item.id is not None:
      return ('item', item.id)
    return ('object', id(item))

  def _tmpl_releasegroupartist(self, item):
    if item.singleton:
      return None

    album_key = self._album_key(item)
    if album_key not in self.releasegroupartists:
      self._log.debug('Finding releasegrouparitst for ' + item.albumartist + ' - ' + item.album)
      if not item.mb_releasegroupid:
        releasegroupartist = item.albumartist
      else:
        try:
          rel = musicbrainzngs.get_release_group_by_id(item.mb_releasegroupid, ['artist-credits'])
          releasegroupartist = rel['release-group']['artist-credit'][0]['artist']['name']
        except Exception:
          releasegroupartist = item.albumartist
          self._log.debug('No MB Credits found for ' + item.albumartist + ' - ' + item.album)

      self.releasegroupartists[album_key] = releasegroupartist

    return self.releasegroupartists[album_key]

  
  def _tmpl_lidarralbum(self, item):
    album_key = self._album_key(item)
    if album_key not in self.lidarralbums:
      sp_rep = {'\\.$': ''}
      sp_rep_clean = {'.': ''}
      sp_regexp = re.compile('|'.join(sp_rep.keys()))
      temp_lidarralbum = sp_regexp.sub(lambda match: sp_rep_clean[match.group(0)], item.album)
      
      rep = {'/': '+', ':': '-', '?': '!'}
      regexp = re.compile('|'.join(map(re.escape, rep)))
      self.lidarralbums[album_key] = regexp.sub(lambda match: rep[match.group(0)], temp_lidarralbum)
    
    return self.lidarralbums[album_key]

  def _tmpl_audiodisctotal(self, item):
    if item.singleton:
      return None

    album_key = self._album_key(item)
    if album_key not in self.audiodisctotals:
      total = 0
      
      if item.disctotal == 1:
        total = 1
      else:
        counted = []
        
        for albumitem in item.get_album().items():
          if albumitem.disc in counted:
            continue
            
          if albumitem.media not in ['Data CD', 'DVD', 'DVD-Video', 'Blu-ray', 'HD-DVD', 'VCD', 'SVCD', 'UMD', 'VHS']:
            total += 1
          
          counted.append(albumitem.disc)
          if len(counted) == item.disctotal:
            break

      self.audiodisctotals[album_key] = None if total == 1 else str(total).zfill(2)

    return self.audiodisctotals[album_key]
