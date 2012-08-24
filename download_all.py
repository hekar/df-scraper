#!/usr/bin/env python

import httplib, urllib, traceback
import sys, os, subprocess
import re

# Return codes from rtmpdump
RD_FAILED = 1
RD_INCOMPLETE = 2

settings = {
  'rtmp' : {
    # Path to rtmpdump
    'rtmp_path' : 'rtmpdump',
    # Urls for listing all videos in dramafever
    'videos_url' : [
      'http://www.dramafever.com/featured/view_all/?page=1',
      'http://www.dramafever.com/featured/view_all/?page=2'
    ],
    # Website name for rtmp
    'website_name' : 'http://www.dramafever.com',
    # Domain
    'domain' : 'www.dramafever.com',
    # Url for SWF file
    'swf_url' : 'http://imgdf-a.akamaihd.net/static/120502/dramafever.commercial-3.2.7.swf',
    # Timeout for video playback
    'timeout' : 60
  },
  'general' : {
    # Start episode
    'start_episode' : 0,
    # End episode
    'end_episode' : 99,
    # Output directory
    'out_dir' : 'C:\\Users\\hekar\\desktop\\tmp\\videos\\',
    # Use regular expressions in searching for the series name
    'series_regex' : False
  }
}

website_name = "http://www.dramafever.com"
swf_url = "http://imgdf-a.akamaihd.net/static/120502/dramafever.commercial-3.2.7.swf"

def download_url(domain, url):
  sys.stdout.write("downloading url: " + url + '\n')
  
  conn = httplib.HTTPConnection(domain)
  conn.request("GET", url)
  response = conn.getresponse()
  data = response.read()
  conn.close()

  return data

def extract_video_data(data):
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

def execute_rtmpdump(output, website_url, swf_url, rtmp_url, rtmp_hash):
  global settings

  rtmp_dump_path = settings['rtmp']['rtmp_path']
  timeout = settings['rtmp']['timeout']
  
  if not output.endswith('.flv'):
    output = output + '.flv'

  command = rtmp_dump_path + " --swfVfy " + swf_url + " -p " + website_url + " -r " + rtmp_url + " -y " + rtmp_hash + " -o " + output + "  -A 0 --timeout " + str(timeout)
  sys.stdout.write(command + '\n')
  return_code = subprocess.call(command.split())
  
  return return_code

def download_video(url, output, website_name, swf_url):
  global RD_FAILED, RD_INCOMPLETE
  global settings
  
  domain = settings['rtmp']['domain']
  
  data = download_url(domain, url)
  video_data = extract_video_data(data)
  
  if video_data == None:
    sys.stdout.write("No playlist on " + url + '\n')
    return False

  # download the subtitles first
  subtitle_url = video_data["subtitle_url"]
  
  # do we actually have a valid subtitle url
  if subtitle_url != '':
    bare_url = url.replace('http://', '')
    full_url = subtitle_url # 'http://' + bare_url[0:bare_url.find('/')] + subtitle_url
    urllib.urlretrieve(full_url, output.replace('.flv', '') + '.srt')
    
  # download the video
  rtmp_url = video_data["rtmp_url"]
  rtmp_hash = video_data["rtmp_hash"]

  return_code = execute_rtmpdump(output, website_name, swf_url, rtmp_url, rtmp_hash)
  
  print "rtmpdump return code: ", return_code
  print return_code == RD_FAILED or RD_INCOMPLETE
  print RD_FAILED, RD_INCOMPLETE
  
  if return_code == RD_FAILED or return_code == RD_INCOMPLETE:
    #raise Exception, "rtmpdump program or download failure"
    pass
  
  return True

def generate_url_list():
  global settings
  
  domain = settings['rtmp']['domain']
  videos_urls = settings['rtmp']['videos_url']
    
  start_episode = settings['general']['start_episode']
  end_episode = settings['general']['end_episode']
  
  url_list = []
  for url in videos_urls:
    data = download_url(domain, url)
    straight_data = data.replace("\n", '')
    drama_urls = re.findall(r'class="engtitledata"><strong><a href=".*?" class="highlight">', straight_data)
    
    for url in drama_urls:
      for i in xrange(start_episode, end_episode):
        url_list.append(url.replace(r'class="engtitledata"><strong><a href="', '').replace(r'" class="highlight">', '').replace("/1/", "/" + str(i) + "/"))
  
  return url_list

def download_series(series):
  global settings
  
  domain = settings['rtmp']['domain']
  out_dir = settings['general']['out_dir']
  
  url_list = generate_url_list()
  for url_end in url_list:
    if settings['general']['series_regex']:
      # TODO: Match with regex
      pass
    else:
      if url_end.lower().find(series.lower()) < 0:
        continue
  
    url = "http://" + domain + url_end + "?ap=1"
    filename = out_dir + url_end.replace('/', '_').replace('_drama_', '').replace("?", '')

    final_name = filename.replace('.flv', '') + '.flv'
    if os.path.exists(final_name):
      sys.stdout.write(final_name + " already exists" + '\n')
      continue
    
    try:
      success = download_video(url, filename, website_name, swf_url)
      if success != True:
        continue
    except:
      os.unlink(final_name)
      return False
      
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
  
