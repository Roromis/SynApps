#!/usr/bin/python2
# -*- coding: utf-8 -*-

from distutils import version

class Application(object):
    def __init__(self, database, infos):
        self.infos = infos
        
        self.icons = database.get_icons(self.infos['id'],
                self.infos['branch'], self.infos['repository'])
        
        self.depends = database.get_depends(self.infos['id'],
                self.infos['branch'], self.infos['repository'])
        
        self.rating = None
        self.votes = None
        self.comments = None
        self.screenshots = None
