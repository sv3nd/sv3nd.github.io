#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

AUTHOR = u'Svend Vanderveken'
SITENAME = u"Svend Vanderveken"
SITEURL = ''

PATH = 'content'

TIMEZONE = 'Europe/Brussels'

DEFAULT_LANG = u'en'

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# Blogroll
LINKS = ()

# Social widget (any font name from http://fontawesome.io/icons/ should work here)
SOCIAL = (
         ("github", 'https://github.com/sv3ndk'),
     	 ("twitter", 'https://twitter.com/sv3ndk'),
     	 ("linkedin", 'https://www.linkedin.com/in/sv3ndk'),
     	 ("stack-overflow", 'https://stackoverflow.com/users/3318335/svend'),
         )

GOOGLE_ANALYTICS = 'UA-101598127-1'

SUMMARY_MAX_LENGTH = 100 

DEFAULT_PAGINATION = 5

# Uncomment following line if you want document-relative URLs when developing
#RELATIVE_URLS = True

THEME = '/home/svend/dev-projects/github.com.sv3ndk/sv3ndk/pelican-hyde'
#THEME_TEMPLATES_OVERRIDES = '/home/svend/dev-projects/github.com.sv3ndk/sv3ndk/pelican-themes'

MARKUP = ('md', 'ipynb')

PLUGIN_PATHS = ['./plugins']
PLUGINS = [ 'ipynb.markup', 'pelican_alias']

IGNORE_FILES = [".ipynb_checkpoints"]

BIO = "I am a freelance data engineer, I currently focus on streaming architectures, Kafka, Scala, Python, SQL,..."
PROFILE_IMAGE = "blog/svend-profile.jpg"

STATIC_PATHS = ['images', 'extra/CNAME']
EXTRA_PATH_METADATA = {'extra/CNAME': {'path': 'CNAME'},}


