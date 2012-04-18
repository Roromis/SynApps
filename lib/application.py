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
import platform

from dependencytree import DependencyTree
from exceptions import *
from functions import get_free_space, zipextractall, rmtree

class Application(object):
    """Classe représentant une application."""
    branches = {
                    'Testing' : 0,
                    'Unstable' : 1,
                    'Stable' : 2
               }
    
    def __init__(self, database, infos):
        """
            Initialisation : récupération des icônes et dépendances dans la base
            de donnée
           
            Arguments :
                database : base de donnée des applications
                infos : dictionnaire contenant les informations de
                        l'applications
                    infos['id'] : Identifiant de l'application
                    infos['branch'] : Brance ('Stable', 'Unstable' ou 'Testing')
                    infos['repository'] : Adresse du dépôt
                    infos['category'] : Catégorie (categorie/sous categorie/...)
                    infos['name'] : Nom de l'application
                    infos['friendly_name'] : Description courte (quelques mots)
                    infos['short_description'] : Description courte (une phrase)
                    infos['long_description'] : Description longue
                    infos['size_c'] : Taille compressé
                    infos['size_u'] : Taille décompressé
                    infos['version'] : Version (chaine de caractères)
                    infos['license'] : License
                    infos['author'] : Mainteneur du paquet
                    infos['show'] : True si le paquet doit être affiché dans
                                    l'interface, False sinon
                    infos['uri'] : adresse du paquet
                    infos['rating'] : Note de l'application
                    infos['votes'] : Nombre de votes (-2 si les évaluations ne
                                     sont pas supportées, -1 si elles n'ont pas
                                     été téléchargées)
        """
        self.database = database
        self.infos = infos
        self.infos['version'] = version.LooseVersion(self.infos['version'])
        
        self.depends = database.get_depends(self.id, self.branch, self.repository)
        self.provides = database.get_provides(self.id)
        self.icons = database.get_icons(self.id, self.branch, self.repository)
        self.links = database.get_links(self.id, self.branch, self.repository)
        
        self.comments = False
        self.screenshots = False
    
    def __eq__(self, y):
        return self.id == y.id
    
    def __getattr__(self, name):
        """
            Permet de renvoyer l'information name si l'attribut n'existe pas.
            Par exemple self.description vaut self.infos['description']
        """
        return self.infos[name]
    
    def __ne__(self, y):
        return self.id != y.id
    
    def _check_provides(self, dependency_tree):
        """
            Lève une exception si des applications fournies sont installées
            
            Arguments :
                dependency_tree : Arbre des dépendances (inversé)
        """
        provides = dependency_tree.get_installed()
        
        if provides != []:
            raise ApplicationNeeded(self.id, [i.id for i in provides])
    
    def _check_size(self, dependency_tree):
        """
            Lève une exception s'il n'y a pas assez de place pour installer
            l'application et ses dépendances
            
            Arguments :
                dependency_tree : Arbre des dépendances
        """
        size_c, size_u = dependency_tree.get_size()
        
        rootpath = self.database.get_config("rootpath")
        tmppath = self.database.get_config("tmppath")
        
        if os.path.splitext(rootpath)[0] == os.path.splitext(tmppath)[0]:
            # Le dossier temporaire et la racine de la Framakey sont sur
            # le même disque
            remaining_space = get_free_space(rootpath) - size_c - size_u
            if remaining_space < 0:
                raise NotEnoughRootFreeSpace(-remaining_space)
        else:
            remaining_space = get_free_space(rootpath) - size_u
            if remaining_space < 0:
                raise NotEnoughRootFreeSpace(-remaining_space)
            
            remaining_space = get_free_space(tmppath) - size_c
            if remaining_space < 0:
                raise NotEnoughTmpFreeSpace(-remaining_space)
    
    def _get_dependency_tree(self, reverse=False):
        """Renvoie l'arbre des dépendances de l'application"""
        return DependencyTree(self.database, self, reverse)
    
    def _get_installation_dirs(self, filename=None):
        """
            Arguments : 
                filename : chemin vers le paquet (facultatif)
            
            Renvoie :
                (application_root, install_dir)
                    application_root : racine de l'application
                    install_dir : dossier dans lequel le paquet doit être extrait
        """
        cfg = ConfigParser({'Show' : 'True', 'InstallDir' : 'Apps', 'ApplicationRoot' : 'Apps/%s' % self.id})
        cfg.add_section('Framakey')
        if filename:
            try:
                package = zipfile.ZipFile(filename, 'r')
            except Exception as e:
                logger.error("Le paquet %s n'est pas une archive zip." % self.id)
                raise InvalidPackage(self, e)
            
            try:
                inifile = package.read(self.id + '/App/AppInfo/installer.ini')
                cfg.read_string(inifile.decode('utf-8'))
            except:
                return os.path.join('Apps', self.id), 'Apps'
        else:
            cfg.read('./cache/installed/' + self.id + '/installer.ini')
            
        
        return cfg.get('Framakey', 'ApplicationRoot'), cfg.get('Framakey', 'InstallDir')
    
    def _install(self, callback):
        """
            Installe l'application (sans dépendances, sans vérifications)
            
            Arguments :
                callback : fonction de signature def callback(progress, message)
        """
        if not self.is_installed():
            logger.info(u"Installation du paquet %s." % (self.id,))
            
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
                    urllib.urlretrieve(self.uri, filename, 
                            lambda c,b,t: callback(
                                    current_step*100/steps + 100*c*b/(t*steps),
                                    u"Téléchargement du paquet")
                            )
                except (urllib2.URLError, urllib2.HTTPError) as e:
                    logger.error(u"Erreur lors du téléchargement:\n"
                                 u''.join(traceback.format_exc()))
                    raise PackageDownloadError(self, e)
                current_step += 1
                
            logger.debug(u"Extraction du paquet.")
            try:
                application_root, install_dir = self._get_installation_dirs(filename)
                zipextractall(filename,
                        os.path.join(self.database.get_config('rootpath'),
                                     install_dir),
                        lambda c,t: callback(
                            current_step*100/steps + 100*c/(t*steps),
                            u"Extraction du paquet")
                        )
            except Exception as e:
                logger.error(u"Le paquet %s est invalide:\n" % (self.id,) + u''.join(traceback.format_exc()))
                raise InvalidPackage(self, e)
            
            logger.debug(u"Suppression du paquet.")
            os.remove(filename)
                
            logger.debug(u"Copie des informations dans le cache.")
            cache = os.path.join('./cache/installed/', self.id)
            appinfo = os.path.join(self.database.get_config("rootpath"),
                                   application_root, 'App', 'AppInfo')
            
            # Copie dans le cache
            os.mkdir(cache)
            if os.path.isdir(appinfo):
                for i in os.listdir(appinfo):
                    shutil.copy(os.path.join(appinfo, i), cache)
            
            # Modification du fichier installer.ini
            self._set_installed_as("depend")
    
    def _set_installed_as(self, installed_as):
        """
            Modifie l'option InstalledAs dans le fichier installer.ini
            
            Arguments :
                installed_as :
                    'depend' si l'application a été installée en tant que
                    dépendance, 'explicit' si l'application a été installée
                    explicitement
        """
        filename = os.path.join('./cache/installed/', self.id, 'installer.ini')
        
        cfg = ConfigParser()
        cfg.optionxform = str   # Pour conserver la casse
        cfg.read(filename)
        
        if not cfg.has_section("Framakey"):
            cfg.add_section("Framakey")
        
        cfg.set("Framakey", "InstalledAs", installed_as)
        
        with open(filename, "w") as f:
            cfg.write(f)
    
    def _set_rating(self, rating, votes):
        """
            Modifie (localement) l'évaluation et les votes de l'application
        """
        self.infos['rating'] = rating
        self.infos['votes'] = votes
        self.database.set_rating(self.id, self.branch, self.repository, rating, votes)
    
    def _uninstall(self, callback):
        """
            Désinstalle l'application
            
            Arguments :
                callback : fonction de signature def callback(progress, message)
        """
        if self.is_installed():
            logger.info(u"Désinstallation du paquet %s." % (self.id,))
            
            application_root, install_dir = self._get_installation_dirs()
            
            # Suppression de l'application
            rmtree(os.path.join(self.database.get_config('rootpath'),
                                application_root), False,
                                lambda c,t: callback(100*c/t,
                                                u"Suppression de l'application")
                    )
            
            # Suppression des fichiers de cache
            rmtree('./cache/installed/' + self.id)
    
    def get_comments(self, limit=10):
        """
            Récupère les commentaires
            
            Arguments :
                limit : nombre maximal de commentaires à récupérer
            
            Renvoie :
                Si le dépôt supporte les commentaires : dictionnaire comments
                    comments['n'] : nombre total de commentaires et
                    comments['comments'] : liste des commentaires ) si le dépôt
                Sinon : None
        """
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
        """Renvoie :
                Si l'application est installée : dictionnaire infos
                    infos['branch'] : Branche de l'application installée
                    infos['version'] : Version de l'application installée
                Sinon : None"""
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
    
    def _get_rating(self):
        """
            Récupère l'évaluation de l'application
            
            Renvoie : None
        """
        logger.debug(u"Téléchargement de l'évaluation de l'application %s." % self.id)
        args = {
                    'application' : self.infos['id'],
                    'branch' : self.infos['branch']
               }
        
        url = self.infos['repository'] + "/rating.php?" + urllib.urlencode(args)
        
        try:
            tmp = json.loads(urllib2.urlopen(url).read())
            self._set_rating(tmp['rating'], tmp['votes'])
        except (urllib2.URLError, urllib2.HTTPError, ValueError):
            self._set_rating(0, -2)
            logger.debug(u"Impossible de télécharger l'évaluation.")
    
    def get_screenshots(self):
        """
            Récupère la liste des captures d'écran
            
            Renvoie :
                Si le dépôt supporte les évaluations : liste des captures d'écran
                Sinon : None
        """
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
    
    def install(self, callbacks={}):
        """Installe l'application et ses dépendances"""
        if self.is_installed():
            logger.warning(u"L'application %s est déjà installée" % self.id)
            raise ApplicationAlreadyInstalled(self)
        
        dependency_tree = self._get_dependency_tree()
        self._check_size(dependency_tree)
        
        callbacks = {'end': [lambda a: a._set_installed_as('explicit')]}
        
        dependency_tree.install(callbacks)
        
    def is_installed(self):
        """
            Renvoie :
                True si l'application est installée
                False sinon
        """
        return os.path.isdir('./cache/installed/' + self.id)
    
    def is_up_to_date(self):
        """
            Renvoie :
                True si l'application est à jour,
                False sinon
        """
        installed = self.get_installed_version()
        
        if installed:
            if installed['version'] > self.version:
                return True
            elif installed['version'] == self.version:
                return self.branch[installed['branch']] > self.branches[self.branch]
            else:
                return False
        else:
            return False
    
    @property
    def rating(self):
        if self.infos['votes'] == -2:
            logger.debug(u"Les évaluations ne sont pas supportée pour l'application %s." % self.id)
            return None
        elif self.infos['votes'] == -1:
            self._get_rating()
        return self.infos['rating']
    
    def uninstall(self, with_provides=False, callbacks={}):
        """
            Désinstalle l'application
            
            Arguments :
                with_provides : True si les applications fournies doivent être
                                désinstallées avant, False sinon
                                Si with_provides vaut false
        """
        if not self.is_installed():
            logger.warning(u"L'application %s n'est pas installée" % self.id)
            raise ApplicationNotInstalled(self)
        
        dependency_tree = self._get_dependency_tree(True)
        if not with_provides:
            self._check_provides(dependency_tree)
        
        dependency_tree.uninstall(callbacks)
    
    @property
    def votes(self):
        if self.infos['votes'] == -2:
            logger.debug(u"Les évaluations ne sont pas supportée pour l'application %s." % self.id)
            return None
        elif self.infos['votes'] == -1:
            self._get_rating()
        return self.infos['rating']
