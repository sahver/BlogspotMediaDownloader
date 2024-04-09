#!/usr/bin/env python3

import argparse
import hashlib
import os
import shutil
import urllib.request
import time

from bs4 import BeautifulSoup
from datetime import datetime
from mimetypes import guess_all_extensions

extrachars = [' ', '-', '_', '.']
MAX_PATH = 260
alphanum = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz01234567789"
delay = 0.1

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
	print('Downloading images from {}'.format(url))
	print('')

	request = urllib.request.Request(url)
	requestData = urllib.request.urlopen(request, None)
	encoding = requestData.headers.get_content_charset()
	str_requestData = requestData.read().decode(encoding)
	soup = BeautifulSoup(str_requestData, 'html.parser')
	posts = soup.findAll("div", {"class" : "post-outer"})

	for post in posts:

		# Create folder with the datetime of the post
		timestamp = datetime.fromisoformat( post.find('abbr', {'class' : 'published'})['title'] )
		folder = args.destination + timestamp.strftime("%Y-%m-%d--%H%M/")
		os.makedirs(os.path.dirname(folder), exist_ok=True)
		
		# Loop through images
		body = post.find("div", {"class" : "post-body"})
		images = body.findAll("img")
		for image in images:
			source = image.parent['href']
#			source = image['src']
			title = source.split("/")[-1]
			title = hashlib.md5(title.encode()).hexdigest() if len(title) > 50 else "".join(c for c in title if c.isalnum() or c in extrachars).rstrip()

			if(source[0] == '/'):
				source = "https:" + source
			fullfilepath = os.path.abspath(folder + title)
			extension = os.path.splitext(source)[1]

			try:
				print('↓ {}/{}'.format(images.index(image)+1, len(images)), '§ {}/{}'.format(posts.index(post)+1, len(posts)), '· ¶ {} > {}'.format(source, fullfilepath))
				
				# Ignore existing files if we are resuming
				if(
					os.path.isfile(fullfilepath)
					or os.path.isfile(fullfilepath + '.jpg')
					or os.path.isfile(fullfilepath + '.jpeg')
					or os.path.isfile(fullfilepath + '.png')
				 ):
					continue

				# Download
				imageresponse = urllib.request.urlopen(source, None)
				# Break in betweeb
				time.sleep(delay)
			except:
				print("Encountered a 404 image")
				continue

			guess = ['']
			if(extension == ''):
				contenttype = imageresponse.info()["Content-Type"]
				guess = guess_all_extensions(contenttype, True)
				fullfilepath += guess[0]

			try:

				file = open(fullfilepath, 'wb')
				shutil.copyfileobj(imageresponse, file)
				downloads += 1
			except Exception as e:
				print("Failed to write to file")
				continue

	next = soup.find("a", {"class" : "blog-pager-older-link"})
	if(next != None):
		url = next["href"]
	else:
		break

print('')
print("Downloaded " + str(downloads) + " images")
print('')
