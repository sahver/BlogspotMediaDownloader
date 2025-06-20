#!/usr/bin/env python3

import argparse
import dateparser
import hashlib
import re
import shutil
import urllib.request
import time

from bs4 import BeautifulSoup
from datetime import datetime
from http.client import IncompleteRead
from mimetypes import guess_all_extensions
from pathlib import Path
from yt_dlp import YoutubeDL

class DownloadFailedException(Exception):
	
	def __init__(self, message):
		self.message = message
		super().__init__(self.message)

	def __str__(self):
		return f'{self.message}'

extrachars = [' ', '-', '_', '.']
MAX_PATH = 200
TIMEOUT = 10

parser = argparse.ArgumentParser(description="test")
parser.add_argument("url", help="URL to the blogspot blog")
parser.add_argument("destination", help="Where to put all the downloaded files")
args = parser.parse_args()

if(not Path(args.destination).exists()):
	print("Destination path does not exist")
	exit()
elif(args.destination[-1] != '/'):
	args.destination += '/'

url = args.url
downloads = 0

try:

	while(True):

		print('')
		print('Scraping {}'.format(url))

		try:
			request = urllib.request.Request(url)
			requestData = urllib.request.urlopen(request, None)
			encoding = requestData.headers.get_content_charset()
			str_requestData = requestData.read().decode(encoding)
			soup = BeautifulSoup(str_requestData, 'html.parser')
			dates = soup.find_all("div", {"class" : "date-outer"})
		except IncompleteRead:
			print('*** Error reading the page, retrying.. ***')
			time.sleep(5)
			continue

		print('')

		#
		# Loop through dates
		#

		for day in dates:

			# Post date
			today = dateparser.parse( day.find('h2', {'class' : 'date-header'}).find('span').get_text() )

			posts = day.find_all('div', {'class' : 'post-outer'})

			#
			# Loop through posts in reverse order
			#

			for index, post in enumerate(reversed(posts), start=1):

				print()
				print(f'{today.strftime("%Y/%m/%d")} ({index})')
				print()

				# Folder structure yyyy/mm/dd/hhmm
				folder = Path( args.destination + (today.strftime(f'%Y/%m/%d/{index}/') if len(posts) > 1 else today.strftime(f'%Y/%m/%d/')) )
				folder.mkdir(parents=True, exist_ok=True)

				post_body = post.find("div", {"class" : "post-body"})
				post_media = post_body.find_all(['img', 'iframe']) + post_body.find_all('a', {'href' : re.compile(r'.*youtube.com/watch.*') })

				#
				# Save body text
				#

				with open(folder / '000.txt', 'w') as f:
					f.write('\n')
					f.write(today.strftime('%Y-%m-%d'))
					f.write('\n')
					f.write('----------')
					f.write('\n')
					f.write('\n')
					f.write(
						post_body.get_text(
							separator='\n\n',
							strip=True
						)
					)

				#
				# Loop through media
				#  

				for media in post_media:

					# URL
					source = media.parent['href'] if media.name == 'img' else ( media['src'] if media.name == 'iframe' else media['href'] )

					# Filename
					title = Path(source).stem

					# Type
					extension = Path(source).suffix if media.name == 'img' else '.mp4'

					# Allowed chars
					title = "".join(c for c in title if c.isalnum() or c in extrachars).rstrip() + extension

					# Shorten if needed
					if len((folder / title).as_posix()) > MAX_PATH:
						title = hashlib.md5(title.encode()).hexdigest() + extension

					# Order
					title = '{:03d}_{}'.format(post_media.index(media)+1, title)

					# Full path
					fullfilepath = folder / title

					#
					# Download
					#

					match media.name:

						# 
						# Images
						#

						case 'img':

							try:
								# Ignore existing files if we are resuming
								if(
									( fullfilepath.is_file() and fullfilepath.stat().st_size > 0 )
									or ( fullfilepath.with_suffix('.jpg').is_file() and fullfilepath.with_suffix('.jpg').stat().st_size > 0 )
									or ( fullfilepath.with_suffix('.jpeg').is_file() and fullfilepath.with_suffix('.jpeg').stat().st_size > 0 )
									or ( fullfilepath.with_suffix('.png').is_file() and fullfilepath.with_suffix('.png').stat().st_size > 0 )
								):
									continue

								# Download
								print('↓ {}/{}'.format(post_media.index(media)+1, len(post_media)), '§ {}/{}'.format(posts.index(post)+1, len(posts)), '· ¶ {} > {}'.format(source, fullfilepath))
								imageresponse = urllib.request.urlopen(source, None, timeout=TIMEOUT)

							except: 
								raise DownloadFailedException(f'Unable to download the image: {source}')


							# If extension is missing then guess or use default
							if(extension == ''):
								guess = ['']
								contenttype = imageresponse.info()["Content-Type"]
								guess = guess_all_extensions(contenttype, True)
								fullfilepath += guess[0] if len(guess[0]) else '.jpg'

							try:
								file = open(fullfilepath, 'wb')
								shutil.copyfileobj(imageresponse, file)
								downloads += 1
							except Exception as e:
								raise DownloadFailedException(f'Unable to write image to disk: {source} > {fullfilepath}')

						#
						# YouTube videos
						#

						case 'a' | 'iframe':

							try:
								# Ignore existing files if we are resuming
								if(
									( fullfilepath.is_file() and fullfilepath.stat().st_size > 0 )
									or ( fullfilepath.with_suffix('.avi').is_file() and fullfilepath.with_suffix('.avi').stat().st_size > 0 )
									or ( fullfilepath.with_suffix('.mp4').is_file() and fullfilepath.with_suffix('.mp4').stat().st_size > 0 )
									or ( fullfilepath.with_suffix('.mov').is_file() and fullfilepath.with_suffix('.mov').stat().st_size > 0 )
									or ( fullfilepath.with_suffix('.webm').is_file() and fullfilepath.with_suffix('.webm').stat().st_size > 0 )
								):
									continue

								# Download
								print('↓ {}/{}'.format(post_media.index(media)+1, len(post_media)), '§ {}/{}'.format(posts.index(post)+1, len(posts)), '· ¶ {} > {}'.format(source, fullfilepath))

								ydl_opts = {
									'outtmpl'				: folder / title,
									'format'				: 'bestvideo+bestaudio/best',
									'merge_output_format'	: 'mp4',
									'quiet'					: True,
									'socket_timeout'		: TIMEOUT
								}

								with YoutubeDL(ydl_opts) as ydl:
									ydl.download([source])

							except:
								raise DownloadFailedException(f'Unable to download Youtube video: {source}')

		#
		# Next..
		#

		next = soup.find("a", {"class" : "blog-pager-older-link"})
		if(next != None):
			url = next["href"]
		else:
			break

	#
	# All done.
	#

	print('Done.')
	print('')

except DownloadFailedException as e:
	print()
	print()
	print(f'{repr(e)}'.strip().replace('\n', ''))
	print()
	print('Download failed, shutting down. Bye.')
	print()
	exit()

except KeyboardInterrupt:
	print()
	print()
	print('Ctrl+C. Bye.')
	print()
	exit()
