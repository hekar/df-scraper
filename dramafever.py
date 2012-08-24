#!/usr/bin/env python
"""
  Scraper for DramaFever
  
  Hekar Khani 2010
"""

import httplib2, urllib, traceback
import sys, os, subprocess
import re

# Return codes from rtmpdump
RD_FAILED = 1
RD_INCOMPLETE = 2

settings = {
  'rtmp' : {
    # Path to rtmpdump
    'rtmp_path' : 'rtmpdump',
    # Website name for rtmp
    'website_name' : 'http://www.dramafever.com',
    # Domain
    'domain' : 'www.dramafever.com',
    # Url for SWF file
    'swf_url' : 'http://imgdf-a.akamaihd.net/static/120502/dramafever.commercial-3.2.7.swf',
    # Timeout for video playback
    'timeout' : 60
  },
  'website' : {
    # Urls for listing all videos in dramafever
    'video_page_urls' : [
      'http://www.dramafever.com/featured/view_all/?page=1',
      'http://www.dramafever.com/featured/view_all/?page=2'
    ]
  },
  'general' : {
    # Start episode
    'start_episode' : 0,
    # End episode
    'end_episode' : 99,
    # Output directory
    'out_dir' : '.'
  }
}

def clean_settings(settings):
  """
    Clean the settings dictionary and get it ready for application usage

    settings - Global settings dictionary
  """

  out = settings['general']['out_dir'] 
  out = out.replace('/', os.path.sep).replace('\\', os.path.sep)
  if not out.endswith(os.path.sep):
    out += os.path.sep

  settings['general']['out_dir'] = out
  
  if not os.path.exists(out):
    os.mkdir(out)

class Video(object):
  def __init__(self, video_url):
    """
      
    """
    self.url = video_url

  def download(self, out):
    """
      Download the video
    """
    global settings
    
    domain = settings['rtmp']['domain']
    swf_url = settings['rtmp']['swf_url']
    website_name = settings['rtmp']['website_name']
    
    video_data = self.video_data()
    
    if video_data == None:
      sys.stdout.write('No playlist on %s\n' % (self.url))
      return False
    
    self.download_subtitle(out, video_data)
    
    # download the video
    rtmp_url = video_data["rtmp_url"]
    rtmp_hash = video_data["rtmp_hash"]
    
    rtmp = Rtmpdump()
    rtmp.execute(out, website_name, swf_url, rtmp_url, rtmp_hash)
    
    return True

  def download_subtitle(self, out, video_data = None):
    """
      Download subtitle for video
      out - Output file path
    """
    if video_data == None:
      video_data = self.video_data(self.url)
    
    subtitle_url = video_data["subtitle_url"]
    
    path = out.replace('.flv', '') + '.srt'
    if subtitle_url != '':
      urllib.urlretrieve(subtitle_url, path)
    
    return path
  
  def video_data(self, url = None):
    """
      Download the video data from the video url
    """
    
    if url == None:
      url = self.url
    
    resp, content = httplib2.Http('.cache').request(url, 'GET')
    return self._parse_data(content)
    
  def _parse_data(self, data):
    """
      Parse raw HTML content to video data

      data - HTML page data
    """
    def extract_url(playlist_data):
      regex = r'url:\s*\".*?\"'
      m = re.findall(regex, playlist_data)
      url = m[0]
      
      return url.strip('url:').strip('"').strip()

    def extract_subtitle(playlist_data):
      regex = r'captionUrl:\s*.*?,'
      m = re.findall(regex, playlist_data)

      try:
        sub = m[0]
      except:
        return ''
      
      return sub.strip("captionUrl:").strip('"').strip(',').strip().strip("'")
      
    straight_data = data.replace("\n", " ")
    regex = r'playlist:\s*\[.*\]'
    r = re.compile(regex)
    m = r.search(straight_data)
    
    # No playlist data on page
    if m == None:
      return None
    
    playlist_data = m.group(0)
    
    url = urllib.unquote(extract_url(playlist_data))
    
    rtmphash = url[url.find('mp4:'):url.find('mp4?')+3]
    url = url[0:url.find('mp4:')] + url[url.find('mp4?')+3:len(url)]
    
    subtitle_url = extract_subtitle(playlist_data)
    
    video_data = {
      "rtmp_url":url,
      "rtmp_hash":rtmphash,
      "subtitle_url":subtitle_url
    }
    
    return video_data

class Rtmpdump(object):
  def __init__(self):
    pass
  
  def execute(self, output, website_url, swf_url, rtmp_url, rtmp_hash):
    global settings

    command = '%s -swfVfy %s -p %s -r %s -y %s -o %s' % (
      settings['rtmp']['rtmp_path'], 
      swf_url,
      website_url,
      rtmp_url,
      rtmp_hash,
      output
    )
    
    sys.stdout.write(command + '\n')
    return_code = subprocess.call(command.split())
    
    return return_code

class ChannelSearcher(object):
  def __init__(self, video_page_urls):
    self.video_page_urls = video_page_urls
    
  def stock_url(self, series):
    """
      Create a stock url where the episode number can be inserted.
      
      For example:
    """
    global settings
    
    for url in self.video_page_urls:
      resp, data = httplib2.Http('.cache').request(url, 'GET')
      straight_data = data.replace("\n", '')
      drama_urls = re.findall(r'class="engtitledata"><strong><a href=".*?" class="highlight">', straight_data)
      
      for url in drama_urls:
        # TODO: Add regex
        if series.lower() in urllib.url2pathname(url.replace('_', ' ').lower()):
          return url.replace(r'class="engtitledata"><strong><a href="', '').replace(r'" class="highlight">', '').replace('/1/', '/%d/')
    
    raise KeyError('Failure to find/extract series url')
  
def download_series(series, filename_format = "%d.flv"):
  global settings
  
  domain = settings['rtmp']['domain']
  out_dir = settings['general']['out_dir']
  start_episode = settings['general']['start_episode']
  end_episode = settings['general']['end_episode']
  
  series_url = ChannelSearcher(settings['website']['video_page_urls']).stock_url(series)
  for episode in xrange(start_episode, end_episode):
    
    sys.stdout.write('Searching for Episode: %d...\n' % (episode))
  
    url = 'http://%s%s?ap=1' % (domain, series_url % (episode))
    
    print url
    
    filename = ''
    if filename_format == None:
      filename = urllib.url2pathname(series_url.replace('/', '_').replace('_drama_', '').replace("?", ''))
      filename = filename.replace('.flv', '')
      split = filename.split('_')[1:]
      filename = '_'.join([split[1], split[0]])
      filename = filename.replace('_', ' ')
      filename += '.flv'
      
      filename = filename % episode
      filename = filename.replace(' ', '_')
    else:
      filename = filename_format % episode
      
    prev_dir = os.getcwd()
    try:
      os.chdir(out_dir)
      
      # Check for video
      if os.path.exists(filename):
        sys.stdout.write(filename + " already exists" + '\n')
        sub_filename = filename.replace('.flv', '')
        if not os.path.exists(sub_filename):
          # Download subtitle
          video = Video(url)
          success = video.download_subtitle(sub_filename)
        continue
     
      video = Video(url)
      success = video.download(filename)
      if success != True:
        continue
    except OSError, e:
      os.unlink(final_name)
      return False
    finally:
      os.chdir(prev_dir)
      
  return True

restart = -1
success = 0
bad_args = 1

def main(args, argc):
  global restart, success, bad_args, settings

  def get_usage_message():
    return """
     USAGE: download_all [command] [args]
     Example usage: download_all --series "Gloria"
     Use the --help switch for this same message

     Possible arguments:
     --start [episode] - Episode number to start from
     --last [episode] - Episode number to stop at
     --series [series] - Download a specific series
     --out [folder] - Output directory
  """.replace('     ', '')
  
  def show_help_and_close():
    sys.stdout.write(get_usage_message() + '\n')
    sys.exit(bad_args)
  
  status = success
  
  series = None
  for i in xrange(1, argc):
    arg = args[i]
    if arg == '--series':
      series = args[i+1]
    elif arg == '--start':
      settings['general']['start_episode'] = int(args[i+1])
    elif arg == '--last':
      settings['general']['end_episode'] = int(args[i+1])
    elif arg == '--out':
      settings['general']['out_dir'] = args[i+1]
    elif arg == '--help':
      show_help_and_close()
    
  if series is None:
    show_help_and_close()
 
  clean_settings(settings)

  rtmp_dump_success = download_series(series)
    
  # Ask the calling function to restart us
  if not rtmp_dump_success:
    status = restart
    
  return status
  
if __name__ == "__main__":
  args = sys.argv
  argc = len(args)
  
  status = restart
  while status == restart:
    status = main(args, argc)

  sys.exit(status)
  
