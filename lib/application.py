#!/usr/bin/python2
# -*- coding: utf-8 -*-

import logging

logger = logging.getLogger('synapps')

import os
from cfg import ConfigParser, NoSectionError, NoOptionError
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
        self.required_by = database.get_required_by(self.id)
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
    
    def _check_required_by(self, dependency_tree):
        """
            Lève une exception si l'application est une dépendance
            d'applications installées
            
            Arguments :
                dependency_tree : Arbre des dépendances (inversé)
        """
        required_by = dependency_tree.get_installed()
        
        if required_by != []:
            raise ApplicationNeeded(self.id, [i.id for i in required_by])
    
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
    
    def _get_installation_infos(self, filename=None):
        """
            Arguments : 
                filename : chemin vers le paquet (facultatif)
            
            Renvoie :
                
        """
        infos = {}
        
        # Emplacement de l'application
        infos['application_root'] = os.path.join('Apps', self.id)
        infos['install_dir'] = 'Apps'
        
        infos['remove'] = {}
        infos['remove']['files'] = []
        infos['remove']['dirs'] = []
        infos['remove']['main'] = ['App', 'Other']
        infos['preserve'] = {}
        infos['preserve']['files'] = []
        infos['preserve']['dirs'] = []
        
        cfg = ConfigParser()
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
                return infos
        else:
            cfg.read('./cache/installed/' + self.id + '/installer.ini')
            
        # Emplacement de l'application
        infos['application_root'] = cfg.get('Framakey', 'ApplicationRoot', 'Apps/%s' % self.id)
        infos['install_dir'] = cfg.get('Framakey', 'InstallDir', 'Apps',)
        
        # Dossier principaux
        if cfg.get('MainDirectories', 'RemoveAppDirectory', 'true').lower() != 'true':
            infos['remove']['main'].remove('App')
        
        if cfg.get('MainDirectories', 'RemoveDataDirectory', 'false').lower() == 'true':
            infos['remove']['main'].append('Data')
        
        if cfg.get('MainDirectories', 'RemoveOtherDirectory', 'true').lower() != 'true':
            infos['remove']['main'].remove('Other')
        
        # Fichiers à supprimer
        infos['remove']['files'] = [i.replace('\\', '/') for i in cfg.getlist('FilesToRemove', 'RemoveFile')]
        
        # Fichiers à conserver
        infos['preserve']['files'] = [i.replace('\\', '/') for i in cfg.getlist('FilesToPreserve', 'PreserveFile')]
        
        # Dossiers à supprimer
        infos['remove']['dirs'] = [i.replace('\\', '/') for i in cfg.getlist('DirectoriesToRemove', 'RemoveDirectory')]
        
        # Dossiers à conserver
        infos['preserve']['dirs'] = [i.replace('\\', '/') for i in cfg.getlist('DirectoriesToPreserve', 'PreserveDirectory')]
        
        return infos
    
    def _install(self, callback, explicit):
        """
            Installe l'application (sans dépendances, sans vérifications)
            
            Arguments :
                callback : fonction de signature def callback(application, type, progress, message, end=False)
                    application : application installée
                    type : type d'opération
                    progress : Avancement (sur 100)
                    message : message décrivant l'opération en cours
                    end : True si l'opération est terminée, False sinon
                explicit : True si l'application est installée explicitement,
                           False si elle est installée en tant que dépendance.
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
                filename = './cache/tmp/' + self.id + '.fmk.zip'
                
                logger.debug(u"Téléchargement du paquet.")
                try:
                    urllib.urlretrieve(self.uri, filename, 
                            lambda c,b,t: callback(self, 'install',
                                    100*(current_step*t + c*b)/(t*steps),
                                    u"Téléchargement du paquet")
                            )
                except (urllib2.URLError, urllib2.HTTPError) as e:
                    logger.error(u"Erreur lors du téléchargement:\n"
                                 u''.join(traceback.format_exc()))
                    raise PackageDownloadError(self, e)
                current_step += 1
                
            logger.debug(u"Extraction du paquet.")
            try:
                infos = self._get_installation_infos(filename)
                zipextractall(filename,
                        os.path.join(self.database.get_config('rootpath'),
                                     infos['install_dir']),
                        lambda c,t: callback(self, 'install',
                            100*(current_step*t + c)/(t*steps),
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
                                   infos['application_root'], 'App', 'AppInfo')
            
            # Copie dans le cache
            os.mkdir(cache)
            if os.path.isdir(appinfo):
                for i in os.listdir(appinfo):
                    shutil.copy(os.path.join(appinfo, i), cache)
            
            # Modification du fichier installer.ini
            if explicit:
                self._set_installed_as("explicit")
            else:
                self._set_installed_as("depend")
                
            callback(self, 'install', 100, u"Installation terminée", True)
    
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
                callback : fonction de signature def callback(application, type, progress, message, end=False)
                    application : application installée
                    type : type d'opération
                    progress : Avancement (sur 100)
                    message : message décrivant l'opération en cours
                    end : True si l'opération est terminée, False sinon
        """
        if self.is_installed():
            logger.info(u"Désinstallation du paquet %s." % (self.id,))
            
            infos = self._get_installation_infos()
            
            # Suppression de l'application
            rmtree(os.path.join(self.database.get_config('rootpath'),
                                infos['application_root']), False,
                                lambda c,t: callback(self, 'uninstall', 100*c/t,
                                                u"Suppression de l'application")
                    )
            
            # Suppression des fichiers de cache
            rmtree('./cache/installed/' + self.id)
            
            callback(self, 'uninstall', 100, u"Désinstallation terminée", True)
    
    def _upgrade(self, callback):
        """
            Met à jour l'application
            
            Arguments :
                callback : fonction de signature def callback(application, type, progress, message, end=False)
                    application : application installée
                    type : type d'opération
                    progress : Avancement (sur 100)
                    message : message décrivant l'opération en cours
                    end : True si l'opération est terminée, False sinon
        """
        if self.is_installed() and not self.is_up_to_date():
            logger.info(u"Mise à jour du paquet %s." % (self.id,))
            
            current_step = 0
            if os.path.isfile(self.uri):
                # Le paquet est un fichier local
                filename = self.uri
                steps = 3
            else:
                steps = 4
                filename = './cache/tmp/' + self.id + '.fmk.zip'
                
                logger.debug(u"Téléchargement du paquet.")
                try:
                    urllib.urlretrieve(self.uri, filename, 
                            lambda c,b,t: callback(self, 'upgrade',
                                    100*(current_step*t + c*b)/(t*steps),
                                    u"Téléchargement du paquet")
                            )
                except (urllib2.URLError, urllib2.HTTPError) as e:
                    logger.error(u"Erreur lors du téléchargement:\n"
                                 u''.join(traceback.format_exc()))
                    raise PackageDownloadError(self, e)
                current_step += 1
            
            logger.debug(u"Suppression de l'ancienne version.")
            callback(self, 'upgrade', 100*current_step/steps, u"Suppression de l'ancienne version")
            #TODO (?) : Progression
            
            try:
                infos = self._get_installation_infos(filename)
            except Exception as e:
                logger.error(u"Le paquet %s est invalide:\n" % (self.id,) + u''.join(traceback.format_exc()))
                raise InvalidPackage(self, e)
            
            for f in infos['remove']['files']:
                os.remove(os.path.join(self.database.get_config('rootpath'), infos['application_root'], f))
            
            for f in infos['preserve']['files']:
                src = os.path.join(self.database.get_config('rootpath'), infos['application_root'], f)
                dst = os.path.join('./cache/tmp', self.id, f)
                if os.path.isfile(src):
                    if not os.path.isdir(os.path.dirname(dst)):
                        os.makedirs(os.path.dirname(dst))
                    os.rename(src, dst)
            
            for d in infos['remove']['dirs']:
                rmtree(os.path.join(self.database.get_config('rootpath'), infos['application_root'], d))
            
            for d in infos['preserve']['dirs']:
                src = os.path.join(self.database.get_config('rootpath'), infos['application_root'], d)
                dst = os.path.join('./cache/tmp', self.id, d)
                if os.path.isfile(src):
                    if not os.path.isdir(os.path.dirname(dst)):
                        os.makedirs(os.path.dirname(dst))
                    os.rename(src, dst)
            
            for d in infos['remove']['main']:
                rmtree(os.path.join(self.database.get_config('rootpath'), infos['application_root'], d))
            
            logger.debug(u"Extraction du paquet.")
            current_step += 1
            
            backupfiles = []
            for root, dirnames, filenames in os.walk(os.path.join('./cache/tmp', self.id)):
                for f in filenames:
                    backupfiles.append(os.path.relpath(os.path.join(root, f), os.path.join('./cache/tmp', self.id)))
            
            try:
                zipextractall(filename,
                        os.path.join(self.database.get_config('rootpath'),
                                     infos['install_dir']),
                        lambda c,t: callback(self, 'upgrade',
                            100*(current_step*t + c)/(t*steps),
                            u"Extraction du paquet"),
                        exclude=backupfiles
                        )
            except Exception as e:
                logger.error(u"Le paquet %s est invalide:\n" % (self.id,) + u''.join(traceback.format_exc()))
                raise InvalidPackage(self, e)
            
            logger.debug(u"Copie de la sauvegarde")
            current_step += 1
            for f in backupfiles:
                src = os.path.join('./cache/tmp', self.id, f)
                dst = os.path.join(self.database.get_config('rootpath'), infos['application_root'], f)
                if os.path.isfile(src):
                    if not os.path.isdir(os.path.dirname(dst)):
                        os.makedirs(os.path.dirname(dst))
                    os.rename(src, dst)
            
            rmtree(os.path.join('./cache/tmp', self.id))
            
            logger.debug(u"Suppression du paquet.")
            os.remove(filename)
            
            logger.debug(u"Copie des informations dans le cache.")
            cache = os.path.join('./cache/installed/', self.id)
            appinfo = os.path.join(self.database.get_config("rootpath"),
                                   infos['application_root'], 'App', 'AppInfo')
            installed_as = self.get_installed_as()
            
            # Copie dans le cache
            rmtree(cache)
            os.mkdir(cache)
            if os.path.isdir(appinfo):
                for i in os.listdir(appinfo):
                    shutil.copy(os.path.join(appinfo, i), cache)
            
            # Modification du fichier installer.ini
            self._set_installed_as(installed_as)
                
            callback(self, 'upgrade', 100, u"Mise à jour terminée", True)
    
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
    
    def get_installed_as(self):
        filename = os.path.join('./cache/installed/', self.id, 'installer.ini')
        cfg = ConfigParser()
        cfg.optionxform = str   # Pour conserver la casse
        cfg.read(filename)
        
        return cfg.get("Framakey", "InstalledAs", "explicit")
    
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
                except NoOptionError: # Rétrocompatibilité
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
    
    def install(self, callback):
        """Installe l'application et ses dépendances"""
        if self.is_installed():
            logger.warning(u"L'application %s est déjà installée" % self.id)
            raise ApplicationAlreadyInstalled(self)
        
        dependency_tree = self._get_dependency_tree()
        self._check_size(dependency_tree)
        
        dependency_tree.install(callback, True)
        
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
                return self.branches[installed['branch']] > self.branches[self.branch]
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
    
    def uninstall(self, with_required_by=False, callback=None):
        """
            Désinstalle l'application
            
            Arguments :
                with_required_by : True si les applications qui dépendent de
                                   l'application à désinstaller doivent être
                                   désinstallées avant, False sinon
        """
        if not self.is_installed():
            logger.warning(u"L'application %s n'est pas installée" % self.id)
            raise ApplicationNotInstalled(self)
        
        dependency_tree = self._get_dependency_tree(True)
        if not with_required_by:
            self._check_required_by(dependency_tree)
        
        dependency_tree.uninstall(callback)
    
    def upgrade(self, callback):
        """Met à jour l'application et vérifie ses dépendances"""
        if not self.is_installed():
            logger.warning(u"L'application %s n'est pas installée" % self.id)
            raise ApplicationNotInstalled(self)
        if self.is_up_to_date():
            logger.warning(u"L'application %s est déjà à jour" % self.id)
            raise ApplicationAlreadyUpToDate(self)
        
        nonexisting_depends = []
        for d in self.depends:
            try:
                app = database.get_application(d)
            except NoSuchApplication:
                # L'application n'existe pas
                nonexisting_depends.append(d)
            else:
                if not app.is_installed():
                    app.install()
        
        self.database.jobs_queue.append_upgrade(self, callback)
    
    @property
    def votes(self):
        if self.infos['votes'] == -2:
            logger.debug(u"Les évaluations ne sont pas supportée pour l'application %s." % self.id)
            return None
        elif self.infos['votes'] == -1:
            self._get_rating()
        return self.infos['rating']
