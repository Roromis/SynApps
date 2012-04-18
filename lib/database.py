#!/usr/bin/python2
# -*- coding: utf-8 -*-

import logging

logger = logging.getLogger('synapps')

import os.path
import sqlite3
import urllib2
import hashlib
import shutil
from configparser import ConfigParser, NoSectionError, NoOptionError
from distutils import version
from locale import strcoll

from category import Category
from application import Application
from operationsqueue import OperationsQueue

from exceptions import *
from functions import get_size, cmp_version, md5file

def get_application_cfg_infos(cfg, section, repository):
    """Récupère les informations sur une application dans le dépôt."""
    branch, id = tuple(section.split(':', 1))
    
    category = cfg.get(section, 'category')
    name = cfg.get(section, 'name')
    friendly_name = cfg.get(section, 'friendly_name')
    short_description = cfg.get(section, 'short_description')
    long_description = cfg.get(section, 'long_description')
    size_c = cfg.getint(section, 'size_c')
    size_u = cfg.getint(section, 'size_u')
    version = cfg.get(section, 'version')
    license = cfg.get(section, 'license')
    author = cfg.get(section, 'author')
    show = cfg.getboolean(section, 'show')
    uri = cfg.get(section, 'uri')
    
    return (id, branch, repository, category, name, friendly_name, 
            short_description, long_description, size_c, size_u, 
            version, license, author, show, uri)

def get_category_cfg_infos(cfg, category):
    """Récupère les informations sur une catégorie dans le dépôt."""
    if cfg.has_option('categories', category):
        icon_uri = cfg.get('categories', category)
    else:
        icon_uri = ''
        
    if cfg.has_option('categories_hash', category):
        newhash = cfg.get('categories_hash', category)
    else:
        newhash = ''
    return (category, icon_uri, newhash, cfg)

def get_category_parent(id):
    return os.path.dirname(id)

def get_repository_cfg(uri):
    """Renvoie : L'objet ConfigParser associé au dépôt"""
    # Téléchargement du dépôt
    try:
        tmp = urllib2.urlopen(uri + '/repository.ini').read()
    except (urllib2.URLError, urllib2.HTTPError) as e:
        logger.warning(u'Impossible de se connecter au dépôt %s' % uri)
        raise RepositoryConnectionError(uri, e)
        
    # Lecture du dépôt
    cfg = ConfigParser()
    try:
        cfg.read_string(tmp.decode('utf-8'))
    except Exception as e:
        logger.warning(u'Le dépôt %s est invalide' % uri)
        raise InvalidRepository(uri, e)
    
    return cfg

class database():
    def __init__(self):
        """Connection à la base de donnée locale des applications"""
        if not os.path.isfile("cache/apps.sqlite"):
            logger.info(u"Le fichier cache/apps.sqlite n'existe pas.")
            logger.info(u"Création de la base de donnée.")
            self.connection = sqlite3.connect("cache/apps.sqlite")
            self.connection.row_factory = sqlite3.Row
            self.curseur = self.connection.cursor()
            
            #  Création des tables
            logger.debug(u"Création des tables.")
            
            # Configuration
            self.curseur.execute("CREATE TABLE config ("
                "name TEXT PRIMARY KEY UNIQUE,"
                "value TEXT)")
            
            # Dépôts
            self.curseur.execute("CREATE TABLE repositories ("
                "uri TEXT PRIMARY KEY UNIQUE,"
                "hash TEXT DEFAULT '',"
                "show_recommendations BOOL DEFAULT 1)")
            
            # Recommendations
            self.curseur.execute("CREATE TABLE recommendations ("
                "repository TEXT,"
                "application TEXT)")
            
            # Catégories
            self.curseur.execute("CREATE TABLE categories ("
                "id TEXT PRIMARY KEY UNIQUE,"
                "hash TEXT)")
            
            # Applications
            self.curseur.execute("CREATE TABLE applications ("
                "id TEXT,"
                "branch TEXT,"
                "repository TEXT,"
                "category TEXT,"
                "name TEXT,"
                "friendly_name TEXT,"
                "short_description TEXT,"
                "long_description TEXT,"
                "size_c INT,"
                "size_u INT,"
                "version TEXT,"
                "rating INT DEFAULT 0,"
                "votes INT DEFAULT -1,"
                "license TEXT,"
                "author TEXT,"
                "show BOOL,"
                "uri TEXT,"
                "PRIMARY KEY (id, branch, repository))")
            
            # Liens
            self.curseur.execute("CREATE TABLE links ("
                "application TEXT,"
                "branch TEXT,"
                "repository TEXT,"
                "title TEXT,"
                "uri TEXT)")
            
            # Dépendances
            self.curseur.execute("CREATE TABLE depends ("
                "application TEXT,"
                "branch TEXT,"
                "repository TEXT,"
                "depend TEXT)")
            
            # Icônes
            self.curseur.execute("CREATE TABLE icons ("
                "application TEXT,"
                "branch TEXT,"
                "repository TEXT,"
                "size INT,"
                "hash TEXT,"
                "PRIMARY KEY (application, branch, repository, size))")
            
            # Ajout des sources par défaut
            logger.debug(u"Ajout des dépôts Framakey.")
            self.add_repository('http://localhost/fk2')

            # Ajout de la configuration par défaut
            logger.debug(u"Ajout de la configuration par défaut.")
            self.set_config('rootpath', '../../Scripts/Framakey')#'..\..\..\..')
            self.set_config('tmppath', './cache/packages')
            self.set_config('version', '0.3 alpha 1')
            self.set_config('show_stable', True)
            self.set_config('show_unstable', True)
            self.set_config('show_testing', True)
            
            # Exécution
            self.connection.commit()
        else:
            logger.debug(u"Le fichier cache/apps.sqlite existe.")
            self.connection = sqlite3.connect("cache/apps.sqlite")
            self.connection.row_factory = sqlite3.Row
            self.curseur = self.connection.cursor()
            
            # On force les évaluations à être mises à jour
            self._execute("UPDATE applications SET votes = -1")
        
        # Tri
        self.connection.create_collation("unicode", strcoll)
        self.connection.create_collation("desc_versions", cmp_version)
        
        # Queue des opérations
        self.operations_queue = OperationsQueue()
        
    def _add_application(self, id, branch, repository, category, name,
                        friendly_name, short_description,
                        long_description, size_c, size_u, version,
                        license, author, show, uri, rating=0, votes=-1):
        """
            Ajoute une application
            
            Arguments :
                id : Identifiant de l'application
                branch : Brance ('Stable', 'Unstable' ou 'Testing')
                repository : Adresse du dépôt
                category : Catégorie (categorie/sous categorie/...)
                name : Nom de l'application
                friendly_name : Description courte (quelques mots)
                short_description : Description courte (une phrase)
                long_description : Description longue
                size_c : Taille compressé
                size_u : Taille décompressé
                version : Version (chaine de caractères)
                license : License
                author : Mainteneur du paquet
                show : True si le paquet doit être affiché dans l'interface
                       False sinon
                uri : adresse du paque
        """
        self.curseur.execute("INSERT INTO applications (id, branch, repository, "
                "category, name, friendly_name, short_description, "
                "long_description, size_c, size_u, version, "
                "license, author, show, uri, rating, votes) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (id, branch, repository,
                category, name, friendly_name, short_description,
                long_description, size_c, size_u, version,
                license, author, show, uri, rating, votes))
    
    def _add_category(self, id, icon_uri=None, newhash=None, cfg=None):
        """
            Ajoute une catégorie ou la modifie si elle existe
            
            Arguments :
                id : Identifiant de la catégorie
                icon_uri : Adresse de l'icône
                newhash : Somme md5 de la nouvelle icône
                cfg : Objet ConfigParser associé au fichier de configuration du
                      dépôt
        """
        hash = self._get_category_hash(id)
        if newhash == None:
            # La catégorie est celle d'une application installée, pas d'informations
             if hash == None:
                # La catégorie n'existe pas
                self.curseur.execute("INSERT INTO categories (id, hash) "
                        "VALUES (?, ?)", (id, ''))
                # On ajoute les parents de la catégorie
                self._add_category(get_category_parent(id))
        elif hash != newhash:
            # Le hash a changé
            if not os.path.isfile('./cache/icons/' + newhash + '.png'):
                try:
                    with open('./cache/icons/' + newhash + '.png', 'wb') as f:
                        f.write(urllib2.urlopen(icon_uri).read())
                except:
                    logger.warning(u"Impossible de télécharger l'icône %s." % icon_uri)
            
            if hash == None:
                # La catégorie n'existe pas
                self.curseur.execute("INSERT INTO categories (id, hash) "
                        "VALUES (?, ?)", (id, newhash))
                # On ajoute les parents de la catégorie
                self._add_category(*get_category_cfg_infos(cfg, get_category_parent(id)))
            else:
                self.curseur.execute("UPDATE categories SET hash = ? "
                        "WHERE id = ?", (newhash, id))
    
    def _add_depend(self, id, branch, repository, depend):
        """
            Ajoute une dépendance
        
            Arguments :
                id : Identifiant de l'application
                branch : Branche de l'application
                repository : Dépôt de l'application
                depend : Identifiant de la dépendance
        """
        self.curseur.execute("INSERT INTO depends (application, branch, repository, depend) "
                "VALUES (?, ?, ?, ?)", (id, branch, repository, depend))
    
    def _add_icon(self, id, branch, repository, size, uri, hash):
        """
            Ajoute une icône d'une application
            
            Arguments :
                id : Identifiant de l'application
                branch : Branche de l'application
                repository : Dépôt de l'application
                size : Taille de l'icône
                uri : Adresse de l'icône
                hash : Somme md5 de l'icône
        """
        self.curseur.execute("INSERT INTO icons (application, branch, repository, size, hash) "
                "VALUES (?,?,?,?,?)", (id, branch, repository, size, hash))
        
        if not os.path.isfile('./cache/icons/' + hash + '.png'):
            try:
                with open('./cache/icons/' + hash + '.png', 'wb') as f:
                    f.write(urllib2.urlopen(uri).read())
            except NoOptionError:
                logger.warning(u"Impossible de télécharger l'icône %s." % uri)
    
    def _add_link(self, id, branch, repository, title, uri):
        """
            Ajoute un lien
            
            Arguments :
                id : Identifiant de l'application
                branch : Branche de l'application
                repository : Dépôt de l'application
                title : Titre du lien
                uri : Adresse du lien
        """
        self.curseur.execute("INSERT INTO links (application, branch, repository, title, uri) "
                "VALUES (?, ?, ?, ?, ?)", (id, branch, repository, title, uri))
    
    def _add_recommendation(self, repository, recommendation):
        """
            Ajoute une recommendation
            
            Arguments :
                repository : Adresse du Dépôt
                recommendation : Identificant de l'application recommendée
        """
        self.curseur.execute("INSERT INTO recommendations (repository, application) "
                "VALUES (?, ?)", (repository, recommendation))
        
    def _execute(self, query, data=()):
        """
            Éxecute une commande SQL nécessitant un "commit" (insertion,
            suppression, création de table...)
            
            Renvoie : l'id de la dernière ligne insérée
        """
        self.curseur.execute(query, data)
        self.connection.commit()
        
        return self.curseur.lastrowid
    
    def _get_application_infos(self, id, branch=None, repository=None, shown=False):
        """
            Arguments :
                id : Identifiant de l'application
                branch : Branche de l'application (facultatif)
                repository : Dépôt de l'application (facultatif)
                shown :
                    True si l'application est visible
                    False sinon
            
            Renvoie : Les informations de l'application correspondante
        """
        if branch == None:
            if repository == None:
                apps = self._query("SELECT * FROM applications WHERE id = ?"
                                  "ORDER BY version COLLATE desc_versions, repository DESC", (id,))
            else:
                apps = self._query("SELECT * FROM applications WHERE id = ? "
                                  "AND repository = ? "
                                  "ORDER BY version COLLATE desc_versions", (id, repository))
            try:
                version = apps[0]['version']
            except IndexError:
                logger.error("L'application (id = %s, branch = %s, repository = %s) n'existe pas." % (id, str(branch), str(repository)))
                raise NoSuchApplication(id, branch, repository)
            
            stable = [i for i in apps if i['branch'] == "Stable" and i['version'] == version]
            unstable = [i for i in apps if i['branch'] == "Unstable" and i['version'] == version]
            testing = [i for i in apps if i['branch'] == "Testing" and i['version'] == version]
            
            if (self.get_config("show_stable") or not shown) and len(stable) > 0:
                return dict(stable[0])
            elif (self.get_config("show_unstable") or not shown) and len(unstable) > 0:
                return dict(unstable[0])
            elif (self.get_config("show_testing") or not shown) and len(testing) > 0:
                return dict(testing[0])
            else:
                raise NoSuchApplication(id, branch, repository)
        else:
            if repository == None:
                apps = self._query("SELECT * FROM applications WHERE id = ? "
                                  "AND branch ? "
                                  "ORDER BY version COLLATE desc_versions, repository DESC", (id, branch))
            else:
                apps = self._query("SELECT * FROM applications WHERE id = ? "
                                  "AND branch = ? "
                                  "AND repository = ? "
                                  "ORDER BY version COLLATE desc_versions", (id, branch, repository))
            if (self.get_config("show_" + branch.lower(), False) or not shown) and len(apps) > 0:
                return dict(apps[0])
            else:
                raise NoSuchApplication(id, branch, repository)
    
    def _get_category_hash(self, id):
        """
            Argument :
                id : Identificant de la catégorie
            
            Renvoie : La somme md5 de l'icône de la catégorie
        """
        try:
            return self._query("SELECT hash FROM categories "
                    "WHERE id = ?", (id,))[0][0]
        except IndexError:
            return None

    def _get_installed_application_cfg_infos(self, id):
        repository = u''
        
        try:
            cfg = ConfigParser({'Show' : 'True', 'InstallDir' : 'Apps', 'ApplicationRoot' : 'Apps/%s' % id})
            cfg.read(['./cache/installed/' + id + '/appinfo.ini', './cache/installed/' + id + '/installer.ini'])
            
            root = os.path.join(self.get_config('rootpath'), cfg.get('Framakey', 'ApplicationRoot'))
            if os.path.exists(root):
                size_u = get_size(root)
            else:
                logger.debug(u"L'application %s n'est plus installée, suppression des fichiers de cache." % id)
                shutil.rmtree('./cache/installed/' + id)
                return None, None, None
            
            try:
                branch = cfg.get('Framakey', 'Branch')
            except NoOptionError:       # Rétrocompatibilité
                branch = cfg.get('Framakey', 'Repository')
            category = cfg.get('Details', 'Category')
            name = cfg.get('Framakey', 'Name')
            friendly_name = cfg.get('Framakey', 'FriendlyName')
            short_description = cfg.get('Details', 'Description')
            long_description = cfg.get('Framakey', 'LongDesc')
            size_c = 0
            
            version = cfg.get('Version', 'PackageVersion')
            license = cfg.get('Framakey', 'License')
            author = cfg.get('Details', 'Publisher')
            show = cfg.getboolean('Framakey', 'Show')
            uri = ''
        except (NoSectionError, NoOptionError):
            logger.debug(u"Les informations de l'application %s sont incomplètes." % id)
            return None, None, None
        
        depends = []
        i = 1
        while cfg.has_option('Framakey', 'Depend%d'%i):
            depends.append(cfg.get('Framakey', 'Depend%d'%i))
            i += 1
        
        links = []
        try:
            links.append(('Fiche Framakey', cfg.get('Details', 'Homepage')))
        except (NoSectionError, NoOptionError):
            pass
        
        try:
            links.append(('Fiche Framasoft', cfg.get('Framakey', 'FramasoftPage')))
        except (NoSectionError, NoOptionError):
            pass
        
        try:
            links.append(('Site Officiel', cfg.get('Framakey', 'AppWebsite')))
        except (NoSectionError, NoOptionError):
            pass
        
        return (id, branch, repository, category, name, friendly_name, 
                short_description, long_description, size_c, size_u, 
                version, license, author, show, uri, 0, -2), links, depends
    
    def _icon_used(self, hash):
        """
            Arguments :
                hash : Somme md5 d'une icône
            
            Renvoie : True si l'icône est utilisée, False sinon.
        """
        if self._query('SELECT COUNT(hash) FROM categories WHERE hash = ?', (hash,))[0][0] > 0:
            # L'icône est utilisée pour une catégorie
            return True
        elif self._query('SELECT COUNT(hash) FROM icons WHERE hash = ?', (hash,))[0][0] > 0:
            # L'icône est utilisée pour une application
            return True
        else:
            return False
    
    def _query(self, query, data=()):
        """Éxecute une commande SQL de type "SELECT"
           Renvoie : les données récupérées"""
        self.curseur.execute(query, data)
        return self.curseur.fetchall()
    
    def _remove_all_from_repository(self, uri):
        """
            Supprime le contenu d'un dépôt
            
            Arguments :
                uri : Adresse du dépôt
        """
        self._execute("DELETE FROM applications WHERE repository = ?", (uri,))
        self._execute("DELETE FROM recommendations WHERE repository = ?", (uri,))
        
        self._execute("DELETE FROM depends WHERE repository = ?", (uri,))
        self._execute("DELETE FROM links WHERE repository = ?", (uri,))
        self._execute("DELETE FROM icons WHERE repository = ?", (uri,))
    
    def _remove_empty_categories(self):
        """Supprime les catégories vides"""
        for category in self.get_categories():
            if category.count_applications() == 0:
                category.remove()
    
    def _remove_old_icons(self):
        """Supprime les icônes inutilisées"""
        for filename in os.listdir("./cache/icons"):
            if not self._icon_used(filename[:-4]):
                os.remove("./cache/icons/" + filename)
    
    def _set_repository_hash(self, uri, hash):
        """
            Modifie la somme md5 associée à un dépôt
            
            Arguments :
                uri : Adresse du dépôt
                hash : Nouvelle somme md5
        """
        self.curseur.execute("UPDATE repositories SET hash = ? WHERE uri = ?", (hash, uri))
    
    def add_repository(self, uri):
        """
            Ajoute un dépôt
            
            Arguments :
                uri : Adresse du Dépôt
        """
        self._execute("INSERT INTO repositories (uri) VALUES (?)", (uri,))
    
    def application_exists(self, id):
        """
            Renvoie :
                True si l'application est dans la base de donnée
                False sinon
        """
        return self._query("SELECT count(id) FROM applications WHERE id = ?", (id,))[0][0] > 0
    
    def count_applications(self, category):
        """
            Renvoie : Le nombre d'applications que contient la catégorie (et ses
                      sous catégories)
        """
        return self._query("SELECT count(id) FROM applications "
                "WHERE category LIKE ?", (category + "%",))[0][0]
    
    def get_application(self, id, branch=None, repository=None):
        """
            Arguments :
                id : Identifiant de l'application
                branch : Branche de l'application (facultatif)
                repository : Dépôt de l'application (facultatif)
            
            Renvoie : l'application correspondante
        """
        return Application(self, self._get_application_infos(id, branch, repository))
    
    def get_applications(self, category=''):
        """
            Arguments :
                category : Identifiant de la Catégorie (facultatif)
            
            Renvoie :
                Les applications que contient la catégorie (et ses sous
                catégories)
        """
        applications = self._query("SELECT * FROM applications "
                "WHERE category LIKE ?", (category + "%",))
        return [Application(self, dict(i)) for i in applications]
    
    def get_categories(self):
        """Renvoie : La liste de toutes les catégories"""
        categories = self._query("SELECT id FROM categories")
        return map(lambda (a,):self.get_category(a), categories)
    
    def get_category(self, id):
        """
            Argument :
                id : Identificant de la catégorie
            
            Renvoie : La catégorie correspondante
        """
        return Category(self, id)
    
    def get_category_icon(self, id):
        """
            Argument :
                id : Identificant de la catégorie
            
            Renvoie : L'icône de la catégorie
        """
        hash = self._get_category_hash(id)
        if hash:
            return './cache/icons/' + hash + '.png'
        else:
            return None

    def get_config(self, name, default=None):
        """
            Arguments :
                name : Nom de la propriété
                default : Valeur par défaut (None par défaut)
            
            Renvoie :
                La valeur de la propriété si elle existe
                La valeur par défaut sinon
        """
        self.curseur.execute("SELECT * FROM config WHERE name = ?", (name,))
        value = self.curseur.fetchone()
        if value == None:
            return default
        else:
            if value['value'] == None:
                return default
            elif value['value'].isdigit():
                return int(value['value'])
            elif value['value'].lower() == 'true':
                return True
            elif value['value'].lower() == 'false':
                return False
            else:
                return value['value']
    
    def get_depends(self, id, branch, repository):
        """
            Arguments :
                id : Identifiant de l'application
                branch : Branche de l'application
                repository : Dépôt de l'application
            
            Renvoie : La liste des dépendances de l'application
        """
        depends = self._query("SELECT depend FROM depends WHERE application = ? "
                    "AND branch = ? AND repository = ?",
                    (id, branch, repository))
        return map(lambda (a,):a, depends)
        
    
    def get_icon_hash(self, id, branch, repository, size):
        """
            Arguments :
                id : Identifiant de l'application
                branch : Branche de l'application
                repository : Dépôt de l'application
                size : Taille de l'icône
            
            Renvoie :
                La somme md5 de l'icône si elle existe
                None sinon
        """
        try:
            return self._query("SELECT hash FROM icons WHERE application = ? "
                    "AND branch = ? AND repository = ? AND size = ? ",
                    (id, branch, repository, size))[0]
        except IndexError:
            return None
    
    def get_icons(self, id, branch, repository):
        """
            Arguments :
                id : Identifiant de l'application
                branch : Branche de l'application
                repository : Dépôt de l'application
            
            Renvoie : Les icônes de l'application
        """
        icons = self._query("SELECT size, hash FROM icons WHERE application = ? AND branch = ? AND repository = ?",
                    (id, branch, repository))
        icons = map(lambda (a,b):(a,'./cache/icons/'+b+'.png'), icons)
        return dict(icons)

    def get_installed_application(self, id):
        """
            Arguments :
                id : Identifiant de l'application
            
            Renvoie :
                Si l'application est correctement installée, les informations
                    locales
                Sinon : None
        """
        try:
            cfg = ConfigParser({'Show' : 'True', 'InstallDir' : 'Apps', 'ApplicationRoot' : 'Apps/%s' % id})
            cfg.read(['./cache/installed/' + id + '/appinfo.ini', './cache/installed/' + id + '/installer.ini'])
            
            infos = {}
            infos['id'] = id
            
            try:
                infos['branch'] = cfg.get('Framakey', 'Branch')
            except NoOptionError:       # Rétrocompatibilité
                infos['branch'] = cfg.get('Framakey', 'Repository')
            infos['repository'] = None
            infos['category'] = cfg.get('Details', 'Category')
            infos['name'] = cfg.get('Framakey', 'Name')
            infos['friendly_name'] = cfg.get('Framakey', 'FriendlyName')
            infos['short_description'] = cfg.get('Details', 'Description')
            infos['long_description'] = cfg.get('Framakey', 'LongDesc')
            infos['size_c'] = 0
            
            root = os.path.join(self.get_config('rootpath'), cfg.get('Framakey', 'ApplicationRoot'))
            if os.path.exists(root):
                infos['size_u'] = get_size(root)
            else:
                logger.debug(u"L'application %s n'est plus installée, suppression des fichiers de cache." % id)
                shutil.rmtree('./cache/installed/' + id)
                return None
            
            infos['version'] = cfg.get('Version', 'PackageVersion')
            infos['rating'] = 0
            infos['votes'] = 0
            infos['license'] = cfg.get('Framakey', 'License')
            infos['author'] = cfg.get('Details', 'Publisher')
            infos['show'] = cfg.getboolean('Framakey', 'Show')
            infos['uri'] = None
        except (NoSectionError, NoOptionError):
            logger.debug(u"Les informations de l'application %s sont incomplètes." % id)
            return None
        
        logger.debug(u"Ajout de %s aux applications installées." % id)
        return Application(self, infos)
    
    def get_installed_applications(self):
        """Renvoie : Les applications installées"""
        logger.info(u"Recherche des applications installées.")
        for id in os.listdir('./cache/installed'):
            if self.application_exists(id):
                logger.debug(u"L'application %s est dans les dépôts." % id)
                yield self.get_application(id)
            else:
                logger.debug(u"L'application %s n'est pas dans les dépôts, récupération des informations." % id)
                application = self.get_installed_application(id)
                if application != None:
                    yield application
    
    def get_links(self, id, branch, repository):
        """
            Arguments :
                id : Identifiant de l'application
                branch : Branche de l'application
                repository : Dépôt de l'application
            
            Renvoie : La liste des liens de l'application
        """
        links = self._query("SELECT title, uri FROM links WHERE application = ? "
                           "AND branch = ? AND repository = ?",
                           (id, branch, repository))
        return map(dict, links)
    
    def get_provides(self, id):
        """
            Arguments :
                id : Identifiant de l'application
            
            Renvoie : La liste des applications installées qui en dépendent
        """
        provides = self._query("SELECT id FROM depends"
                              "WHERE depend = ? AND repository = ''", (id,))
        return map(lambda (a,):a, provides)
    
    def get_repositories(self):
        """Renvoie : La liste des dépôts"""
        return self._query('SELECT uri, hash FROM repositories')
    
    def get_subcategories(self, id=''):
        """
            Arguments :
                id : Identifiant de la catégorie
            
            Renvoie : Les sous catégories"""
        return [i for i in self.get_categories() if get_category_parent(i) == id]
    
    def remove_category(self, id):
        """
            Supprime une catégorie
            
            Arguments :
                id : Identifiant de la catégorie
        """
        self.curseur.execute("DELETE FROM categories WHERE id = ?", (id,))
    
    def set_config(self, name, value):
        """
            Modifie (ou crée) une propriété
            
            Arguments :
                name : Nom de la propriété
                value : Nouvelle valeur
        """
        self.curseur.execute("SELECT * FROM config WHERE name = ?", (name,))
        if self.curseur.fetchone() == None:
            self._execute("INSERT INTO config (name, value) VALUES (?, ?)", (name, str(value)))
        else:
            self._execute("UPDATE config SET value = ? WHERE name = ?", (str(value), name))
    
    def set_rating(self, id, branch, repository, rating, votes):
        """
            Modifie localement l'évaluation de l'application
        
            Arguments :
                id : Identifiant de l'application
                branch : Branche de l'application
                repository : Dépôt de l'application
                rating : Nouvelle note
                votes : Nombre de votes
        """
        self._execute("UPDATE applications SET rating = ?, votes = ? "
                     "WHERE id = ? AND branch = ? AND repository = ?",
                     (rating, votes, id, branch, repository))
    
    def update(self, force=False):
        """
            Met à jour la base de donnée
            
            Arguments :
                force :
                    True si la mise à jour est forcée (les dépôts sont mis à
                        jour qu'ils aient été modifié ou non)
                    False sinon
        """
        logger.info(u"Mise à jour des dépôts.")
        for repository in self.get_repositories():
            try:
                new_hash = urllib2.urlopen(repository['uri'] + '/repository.ini.hash').read()
            except (urllib2.URLError, urllib2.HTTPError):
                new_hash = None
            
            if repository['hash'] == new_hash and not force:
                logger.debug(u"Le dépôt %s n'a pas été modifié." % repository['uri'])
            else:
                logger.debug(u"Le dépôt %s a été modifié (ou la mise à jour a été forcée).", repository['uri'])
                self._set_repository_hash(repository['uri'], new_hash)
                
                logger.debug(u"Suppression des anciennes applications du dépôt.")
                self._remove_all_from_repository(repository['uri'])
                
                cfg = get_repository_cfg(repository['uri'])
                
                logger.debug(u"Insertion des recommendations du dépôt.")
                i = 1
                while cfg.has_option('repository', 'recommendation%d'%i):
                    self._add_recommendation(repository['uri'], cfg.get('repository', 'recommendation%d'%i))
                    i += 1
                
                logger.debug(u"Insertion des applications du dépôt.")
                for section in cfg.sections():
                    if section not in ['repository', 'categories', 'categories_hash']:
                        logger.debug(u"Insertion de %s." % section)
                        try:
                            branch, id = tuple(section.split(":", 1))
                            self._add_application(*get_application_cfg_infos(cfg, section, repository['uri']))
                            self._add_category(*get_category_cfg_infos(cfg, cfg.get(section, 'category')))
                            
                            i = 1
                            while cfg.has_option(section, 'link%d'%i):
                                self._add_link(id, branch, repository['uri'], cfg.get(section, 'link%d_name'%i), cfg.get(section, 'link%d'%i))
                                i += 1
                            
                            i = 1
                            while cfg.has_option(section, 'depend%d'%i):
                                self._add_depend(id, branch, repository['uri'], cfg.get(section, 'depend%d'%i))
                                i += 1
                            
                            for size in [32,48,64,128]:
                                if cfg.has_option(section, 'icon_%d'%size):
                                    self._add_icon(id, branch, repository['uri'], size, cfg.get(section, 'icon_%d'%size), cfg.get(section, 'icon_%d_hash'%size))
                            
                        except (NoSectionError, NoOptionError):
                            logger.warning(u"Les informations de l'application %s du dépôt %s sont incomplète." % (section,repository['uri']))
        
        
        logger.info(u"Recherche des applications installées.")
        
        logger.debug(u"Suppression des applications installées de la base de donnée.")
        self._remove_all_from_repository('')
        
        logger.debug(u"Insertion des applications installées.")
        for id in os.listdir('./cache/installed'):
            infos, links, depends = self._get_installed_application_cfg_infos(id)
            if infos:
                self._add_application(*infos)
                self._add_category(infos[3])
                
                for title, uri in links:
                    self._add_link(id, infos[1], u'', title, uri)
                
                for depend in depends:
                    self._add_depend(id, infos[1], u'', depend)
                
                for size in [32,48,64,128]:
                    filename = './cache/installed/%s/appicon_%d.png' % (id, size)
                    if os.path.isfile(filename):
                        self._add_icon(id, infos[1], u'', size, filename, md5file(filename))
        
        self.connection.commit()
        
        self._remove_empty_categories()
        self._remove_old_icons()
        
        self.connection.commit()
        logger.info(u"Fin de la mise à jour des dépôts.")
