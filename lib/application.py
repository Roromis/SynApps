#!/usr/bin/python2
# -*- coding: utf-8 -*-

import logging

logger = logging.getLogger('synapps')

import os
from configparser import ConfigParser, NoSectionError, NoOptionError
import urllib, urllib2
import json
from distutils import version
import traceback
import zipfile
import shutil

## Exceptions ##
class ApplicationAlreadyInstalled(Exception):
    """Exception levée lorsque l'application à installer est déjà
       installée.

    Attributs:
        application : Classe application
    """
    def __init__(self, application):
        self.application = application

class PackageDownloadError(Exception):
    """Exception levée lorsque le paquet ne peut pas être téléchargé.

    Attributs:
        application : Classe application
        error       : erreur ayant déclenché cette exception
    """
    def __init__(self, application, error):
        self.application = application
        self.error = error

class InvalidPackage(Exception):
    """Exception levée lorsqu'il est impossible de lire le contenu d'un
       paquet.

    Attributs:
        application : Classe application
        error       : erreur ayant déclenché cette exception
    """
    def __init__(self, application, error):
        self.application = application
        self.error = error

## Fonctions ##
def zipextractall(zip, path=None, callback=None, members=None, pwd=None, exclude=[]):
	"""Extract all members from the archive to the current working
	   directory. `path' specifies a different directory to extract to.
	   `members' is optional and must be a subset of the list returned
	   by namelist().
	"""
	zip = zipfile.ZipFile(zip, 'r')
	
	if callback is None:
		def callback(currentsize, totalsize):
			return None
	
	if members is None:
		members = zip.namelist()
	
	for i in exclude:
		for j in members:
			if os.path.normpath(j).startswith(i):
				members.remove(j)
	
	zipsize = 0
	for infos in zip.infolist():
		zipsize += infos.file_size
	dirsize = 0
	
	for zipinfo in members:
		zip.extract(zipinfo, path, pwd)
		dirsize += zip.getinfo(zipinfo).file_size
		callback(dirsize, zipsize)

	zip.close()

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
                try:
                    infos['branch'] = cfg.get('Framakey', 'Branch')
                except NoOptionError:       # Rétrocompatibilité
                    infos['branch'] = cfg.get('Framakey', 'Repository')
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
    
    def install(self, callback, *args, **kwargs):
        """Installe l'application"""
        if self.is_installed():
            logger.warning(u"L'application %s est déjà installée" % self.id)
            raise ApplicationAlreadyInstalled(self)
        else:
            logger.info(u"Installation du paquet %s." % self.id)
            
            current_step = 0
            if os.path.isfile(self.uri):
                # Le paquet est un fichier local
                filename = self.uri
                steps = 1
            else:
                steps = 2
                filename = './cache/packages/' + self.id + '.fmk.zip'
                
                logger.debug(u"Téléchargement du paquet.")
                try:
                    urllib.urlretrieve(self.uri, filename, lambda c,b,t: callback(current_step*100/steps + 100*c*b/(t*steps), "Téléchargement du paquet", *args, **kwargs))
                except (urllib2.URLError, urllib2.HTTPError) as e:
                    logger.error(u"Erreur lors du téléchargement:\n" + u''.join(traceback.format_exc()))
                    raise PackageDownloadError(self, e)
                current_step += 1
                
            logger.debug(u"Extraction du paquet.")
            try:
                application_root, install_dir = self.get_installation_dirs(filename)
                zipextractall(filename,
                        os.path.join(self.database.get_config('rootpath'), install_dir),
                        lambda c,t: callback(current_step*100/steps + 100*c/(t*steps), "Extraction du paquet", *args, **kwargs))
            except Exception as e:
                logger.error(u"Le paquet %s est invalide:\n" % self.id + u''.join(traceback.format_exc()))
                raise InvalidPackage(self, e)
            
            logger.debug(u"Suppression du paquet.")
            os.remove(filename)
                
            logger.debug(u"Copie des informations dans le cache.")
            cache = os.path.join('./cache/installed/', self.id)
            appinfo = os.path.join(self.database.get_config("rootpath"), application_root, 'App', 'AppInfo')
            os.mkdir(cache)
            if os.path.isdir(appinfo):
                for i in os.listdir(appinfo):
                    shutil.copy(os.path.join(appinfo, i), cache)
    
    def get_installation_dirs(self, filename):
        try:
            package = zipfile.ZipFile(filename, 'r')
        except Exception as e:
            logger.error("Le paquet %s n'est pas une archive zip." % self.id)
            raise InvalidPackage(self, e)
        
        try:
            inifile = package.read(self.id + '/App/AppInfo/installer.ini')
            cfg = ConfigParser()
            cfg.read_string(inifile.decode('utf-8'))
        except KeyError:
            return os.path.join('Apps', self.id), 'Apps'
        
        try:
            install_dir = cfg.get('Framakey', 'InstallDir')
        except (NoOptionError, NoSectionError):
            install_dir = 'Apps'
        
        try:
            application_root = cfg.get('Framakey', 'InstallDir')
        except (NoOptionError, NoSectionError):
            application_root = os.path.join('Apps', self.id)
        
        return application_root, install_dir
        
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
