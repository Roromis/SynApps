#!/usr/bin/python2
# -*- coding: utf-8 -*-

import urllib, urllib2
import json

class Application(object):
    def __init__(self, database, infos):
        """Initialisation : récupération des icônes et dépendances dans
           la base de donnée"""
        self.infos = infos
        
        self.icons = database.get_icons(self.infos['id'],
                self.infos['branch'], self.infos['repository'])
        
        self.depends = database.get_depends(self.infos['id'],
                self.infos['branch'], self.infos['repository'])
        
        self.rating = False
        self.votes = False
        self.comments = False
        self.screenshots = False
    
    def get_rating(self):
        """Récupère la note de l'application
           Renvoie : d (où d['rating'] est la note et d['votes'] le
                     nombre de votes) si le dépôt le permet, None sinon"""
        if self.rating == False:
            args = {
                        'application' : self.infos['id'],
                        'branch' : self.infos['branch']
                   }
            
            url = self.infos['repository'] + "/rating.php?" + urllib.urlencode(args)
            
            try:
                self.rating = json.loads(urllib2.urlopen(url).read())
            except (urllib2.URLError, urllib2.HTTPError, ValueError):
                self.rating = None
        
        return self.rating
    
    def get_screenshots(self):
        """Récupère la liste des captures d'écran
           Renvoie : liste de lien vers les captures d'écran si le dépôt
                     le permet, None sinon"""
        if self.screenshots == False:
            args = {
                        'application' : self.infos['id'],
                        'branch' : self.infos['branch']
                   }
            
            url = self.infos['repository'] + "/screenshots.php?" + urllib.urlencode(args)
            
            try:
                self.screenshots = json.loads(urllib2.urlopen(url).read())
            except (urllib2.URLError, urllib2.HTTPError, ValueError):
                self.screenshots = None
        
        return self.screenshots
    
    def get_comments(self, limit=10):
        """Récupère les commentaires
           Renvoie : d (où d['n'] est le nombre de commentaires et
                     d['votes'] la liste des commentaires ) si le dépôt
                     le permet, None sinon"""
        if self.comments == False:
            args = {
                        'application' : self.infos['id'],
                        'branch' : self.infos['branch'],
                        'limit' : limit
                   }
            
            url = self.infos['repository'] + "/comments.php?" + urllib.urlencode(args)
            
            try:
                self.comments = json.loads(urllib2.urlopen(url).read())
            except (urllib2.URLError, urllib2.HTTPError, ValueError):
                self.comments = None
        
        return self.comments
