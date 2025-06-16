#!/usr/bin/env python3

import argparse
import hashlib
import os
import re
import shutil
import urllib.request
import time

from bs4 import BeautifulSoup
from datetime import datetime
from http.client import IncompleteRead
from mimetypes import guess_all_extensions
from pytube import extract, YouTube

extrachars = [' ', '-', '_', '.']
MAX_PATH = 200

parser = argparse.ArgumentParser(description="test")
parser.add_argument("url", help="URL to the blogspot blog")
parser.add_argument("destination", help="Where to put all the downloaded files")
args = parser.parse_args()

if(not os.path.exists(args.destination)):
	print("Destination path does not exist")
	exit()
elif(args.destination[-1] != '/'):
	args.destination += '/'

url = args.url
downloads = 0

while(True):

	print('')
	print('Scraping {}'.format(url))

	try:
		request = urllib.request.Request(url)
		requestData = urllib.request.urlopen(request, None)
		encoding = requestData.headers.get_content_charset()
		str_requestData = requestData.read().decode(encoding)
		soup = BeautifulSoup(str_requestData, 'html.parser')
		posts = soup.find_all("div", {"class" : "post-outer"})
	except IncompleteRead:
		print('*** Error reading the page, retrying.. ***')
		time.sleep(5)
		continue

	print('')

	#
	# Loop through posts
	#

	for post in posts:

		# Create folder with the datetime of the post
		timestamp = datetime.fromisoformat( post.find('abbr', {'class' : 'published'})['title'] )
		# Convert time to system timezone
		timestamp = timestamp.astimezone()
		# Folder structure yyyy/mm/dd/hhmm
		folder = args.destination + timestamp.strftime("%Y/%m/%d/%H%M/")
		os.makedirs(os.path.dirname(folder), exist_ok=True)

		post_body = post.find("div", {"class" : "post-body"})
		post_media = post_body.find_all(['img', 'iframe']) + post_body.find_all('a', {'href' : re.compile(r'.*youtube.com/watch.*') })

		#
		# Save body text
		#

		with open(os.path.abspath(folder + '000.txt'), 'w') as f:
			f.write('\n')
			f.write(timestamp.strftime("%Y-%m-%d %H:%M"))
			f.write('\n')
			f.write('----------------')
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

			# Absolute URL
			if(source[0] == '/'):
				source = "https:" + source

			# Filename
			title = os.path.splitext( os.path.basename(source) )[0] if media.name == 'img' else extract.video_id(source)

			# Type
			extension = os.path.splitext(source)[1] if media.name == 'img' else '.mp4'

			# Allowed chars
			title = "".join(c for c in title if c.isalnum() or c in extrachars).rstrip() + extension

			# Shorten if needed
			if len(os.path.abspath(folder + title)) > MAX_PATH:
				title = hashlib.md5(title.encode()).hexdigest() + extension

			# Order
			title = '{:03d}_{}'.format(post_media.index(media)+1, title)

			# Full path
			fullfilepath = os.path.abspath(folder + title)

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
							( os.path.isfile(fullfilepath) and os.path.getsize(fullfilepath) > 0 )
							or ( os.path.isfile(fullfilepath + '.jpg') and os.path.getsize(fullfilepath + '.jpg') > 0 )
							or ( os.path.isfile(fullfilepath + '.jpeg') and os.path.getsize(fullfilepath + '.jpeg') > 0 )
							or ( os.path.isfile(fullfilepath + '.png') and os.path.getsize(fullfilepath + '.png') > 0 )
						):
							continue

						# Download
						print('↓ {}/{}'.format(post_media.index(media)+1, len(post_media)), '§ {}/{}'.format(posts.index(post)+1, len(posts)), '· ¶ {} > {}'.format(source, fullfilepath))
						imageresponse = urllib.request.urlopen(source, None)
					except:
						print('*** Unable to download the image ***')
						continue

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
						print("Failed to write to file")
						continue

				#
				# YouTube videos
				#

				case 'a' | 'iframe':

					try:
						# Ignore existing files if we are resuming
						if(
							( os.path.isfile(fullfilepath) and os.path.getsize(fullfilepath) > 0 )
							or ( os.path.isfile(fullfilepath + '.avi') and os.path.getsize(fullfilepath + '.avi') > 0 )
							or ( os.path.isfile(fullfilepath + '.mp4') and os.path.getsize(fullfilepath + '.mp4') > 0 )
							or ( os.path.isfile(fullfilepath + '.mov') and os.path.getsize(fullfilepath + '.mp4') > 0 )
							or ( os.path.isfile(fullfilepath + '.webm') and os.path.getsize(fullfilepath + '.mp4') > 0 )
						):
							continue

						# Download
						print('↓ {}/{}'.format(post_media.index(media)+1, len(post_media)), '§ {}/{}'.format(posts.index(post)+1, len(posts)), '· ¶ {} > {}'.format(source, fullfilepath))
						yt = YouTube(source).streams
						yt = yt.filter(progressive=True, file_extension='mp4')
						yt = yt.order_by('resolution').desc()
						yt.first().download(output_path=os.path.abspath(folder), filename=title, skip_existing=False)
					except:
						print('*** Unable to download Youtube video ***')
						continue

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
