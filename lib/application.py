#!/usr/bin/python2
# -*- coding: utf-8 -*-

import logging

logger = logging.getLogger('synapps')

import os
from configparser import ConfigParser, NoSectionError, NoOptionError
import urllib, urllib2
import json
from distutils import version

class Application(object):
    branches = {
                    'Testing' : 0,
                    'Unstable' : 1,
                    'Stable' : 2
               }
    
    def __init__(self, database, infos):
        """Initialisation : récupération des icônes et dépendances dans
           la base de donnée"""
        self.database = database
        self.infos = infos
        self.infos['version'] = version.LooseVersion(self.infos['version'])
        
        self.icons = database.get_icons(self.id, self.branch, self.repository)
        
        self.depends = database.get_depends(self.id, self.branch, self.repository)
        
        self.comments = False
        self.screenshots = False

    def __getattr__(self, name):
        return self.infos[name]
    
    def get_comments(self, limit=10):
        """Récupère les commentaires
           Renvoie : d (où d['n'] est le nombre de commentaires et
                     d['votes'] la liste des commentaires ) si le dépôt
                     le permet, None sinon"""
        if self.repository == None:
            # Application locale non présente dans les dépôts
            return None
        
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
    
    def get_installed_version(self):
        """Renvoie : La version installée, ou None si l'application
           n'est pas installée"""
        if os.path.isfile('./cache/installed/' + self.id + '/appinfo.ini'):
            cfg = ConfigParser()
            cfg.read('./cache/installed/' + self.id + '/appinfo.ini')
            
            infos = {}
            
            try:
                infos['branch'] = cfg.get('Framakey', 'Repository')     # À modifier dans les appinfo.ini
                infos['version'] = version.LooseVersion(cfg.get('Version', 'PackageVersion'))
            except (NoSectionError, NoOptionError):
                return None
            
            return infos
        else:
            return None
    
    def get_rating(self):
        """Récupère la note de l'application
           Renvoie : (note, votes) si le dépôt le permet, None sinon"""
        if self.repository == None:
            # Application locale non présente dans les dépôts
            return None
        
        if self.votes == -2:
            logger.debug(u"Les évaluations ne sont pas supportée pour l'application %s." % self.id)
            return None
        elif self.votes == -1:
            logger.debug(u"Téléchargement de l'évaluation de l'application %s." % self.id)
            args = {
                        'application' : self.infos['id'],
                        'branch' : self.infos['branch']
                   }
            
            url = self.infos['repository'] + "/rating.php?" + urllib.urlencode(args)
            
            try:
                tmp = json.loads(urllib2.urlopen(url).read())
                self.set_rating(tmp['rating'], tmp['votes'])
            except (urllib2.URLError, urllib2.HTTPError, ValueError):
                self.set_rating(0, -2)
                logger.debug(u"Impossible de télécharger l'évaluation.")
                return None
        
        return (self.rating, self.votes)
    
    def get_screenshots(self):
        """Récupère la liste des captures d'écran
           Renvoie : liste de lien vers les captures d'écran si le dépôt
                     le permet, None sinon"""
        if self.repository == None:
            # Application locale non présente dans les dépôts
            files = os.listdir('./cache/installed/' + id)
            screenshots = [i for i in files if i.startswith('screenshot')]
            return ['./cache/installed/' + id + '/' + i for i in screenshots]
        
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
    
    def is_installed(self):
        """Renvoie : True si l'application est installée, False sinon."""
        return os.path.isdir('./cache/installed/' + self.id)
    
    def is_up_to_date(self):
        """Renvoie : True si l'application est à jour, False sinon."""
        installed = get_installed_version()
        
        if installed:
            if installed['version'] > self.version:
                return True
            elif installed['version'] == self.version:
                return self.branch[installed['branch']] > self.branches[self.branch]
            else:
                return False
        else:
            return False
    
    def set_rating(self, rating, votes):
        """Modifie l'évaluation et les votes de l'application"""
        self.rating = rating
        self.votes = votes
        self.database.set_rating(self.id, self.branch, self.repository, rating, votes)
