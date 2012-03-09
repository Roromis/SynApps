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

def cmp_version(a,b):
    """Compare deux chaînes représentant une version."""
    return -cmp(version.LooseVersion(a), version.LooseVersion(b))

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
    except:
        logger.warning(u'Impossible de se connecter au dépôt %s' % uri)
        raise Exception('Impossible de se connecter au dépôt %s' % uri)
        
    # Lecture du dépôt
    cfg = ConfigParser()
    try:
        cfg.read_string(tmp.decode('utf-8'))
    except:
        logger.warning(u'Le dépôt %s est invalide' % uri)
        raise Exception('Le dépôt %s est invalide' % uri)
    
    return cfg

def get_size(path):
    """Renvoie : la taille du dossier ou fichier path"""
    size = 0
    if os.path.isfile(path):
        size = os.path.getsize(path)
    elif os.path.isdir(path):
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                size += os.path.getsize(os.path.join(dirpath, filename))
    return size

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
                "show_recommendations BOOL DEFAULT 1,"
                "show_stable BOOL DEFAULT 1,"
                "show_unstable BOOL DEFAULT 1,"
                "show_testing BOOL DEFAULT 1)")
            
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
            self.set_config('rootpath', '..')#'..\..\..\..')
            self.set_config('version', '0.3 alpha 1')
            
            # Exécution
            self.connection.commit()
        else:
            logger.debug(u"Le fichier cache/apps.sqlite existe.")
            self.connection = sqlite3.connect("cache/apps.sqlite")
            self.connection.row_factory = sqlite3.Row
            self.curseur = self.connection.cursor()
            
            # On force les évaluations à être mises à jour
            self.execute("UPDATE applications SET votes = -1")
        
        # Tri
        self.connection.create_collation("unicode", strcoll)
        self.connection.create_collation("desc_versions", cmp_version)
    
    def add_application(self, id, branch, repository, category, name,
                        friendly_name, short_description,
                        long_description, size_c, size_u, version,
                        license, author, show, uri):
        """Ajoute une application"""
        self.curseur.execute("INSERT INTO applications (id, branch, repository, "
                "category, name, friendly_name, short_description, "
                "long_description, size_c, size_u, version, "
                "license, author, show, uri) VALUES "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (id, branch, repository,
                category, name, friendly_name, short_description,
                long_description, size_c, size_u, version,
                license, author, show, uri))
    
    def add_category(self, id, icon_uri, newhash, cfg):
        """Ajoute une catégorie ou la modifie si elle existe"""
        hash = self.get_category_hash(id)
        if hash != newhash:
            if not os.path.isfile('./cache/icons/' + newhash + '.png'):
                try:
                    with open('./cache/icons/' + newhash + '.png', 'wb') as f:
                        f.write(urllib2.urlopen(icon_uri).read())
                except:
                    logger.warning(u"Impossible de télécharger l'icône %s." % icon_uri)
            
            if hash == None:
                self.curseur.execute("INSERT INTO categories (id, hash) "
                        "VALUES (?, ?)", (id, newhash))
                # On ajoute les parents de la catégorie
                self.add_category(*get_category_cfg_infos(cfg, get_category_parent(id)))
            else:
                self.curseur.execute("UPDATE categories SET hash = ? "
                        "WHERE id = ?", (newhash, id))
    
    def add_depend(self, id, branch, repository, depend):
        """Ajoute une dépendance"""
        self.curseur.execute("INSERT INTO depends (application, branch, repository, depend) "
                "VALUES (?, ?, ?, ?)", (id, branch, repository, depend))
    
    def add_icon(self, id, branch, repository, size, uri, hash):
        """Ajoute une icône"""
        self.curseur.execute("INSERT INTO icons (application, branch, repository, size, hash) "
                "VALUES (?,?,?,?,?)", (id, branch, repository, size, hash))
        
        if not os.path.isfile('./cache/icons/' + hash + '.png'):
            try:
                with open('./cache/icons/' + hash + '.png', 'wb') as f:
                    f.write(urllib2.urlopen(uri).read())
            except NoOptionError:
                logger.warning(u"Impossible de télécharger l'icône %s." % uri)
    
    def add_link(self, id, branch, repository, title, uri):
        """Ajoute un lien"""
        self.curseur.execute("INSERT INTO links (application, branch, repository, title, uri) "
                "VALUES (?, ?, ?, ?, ?)", (id, branch, repository, title, uri))
    
    def add_recommendation(self, repository, recommendation):
        """Ajoute une recommendation"""
        self.curseur.execute("INSERT INTO recommendations (repository, application) "
                "VALUES (?, ?)", (repository, recommendation))
    
    def add_repository(self, uri):
        """Ajoute un dépôt"""
        self.execute("INSERT INTO repositories (uri) VALUES (?)", (uri,))
    
    def application_exists(self, id):
        """Renvoie : True si l'application est dans la base de donnée,
                     False sinon"""
        return self.query("SELECT count(id) FROM applications WHERE id = ?", (id,))[0][0] > 0
    
    def count_applications(self, category):
        """Renvoie : Le nombre d'applications que contient la catégorie
                     (et ses sous catégories)"""
        return self.query("SELECT count(id) FROM applications "
                "WHERE category LIKE ?", (category + "%",))[0][0]
        
    def execute(self, query, data=()):
        """Éxecute une commande SQL nécessitant un "commit" (insertion,
           suppression, création de table...)
           Renvoie : l'id de la dernière ligne insérée"""
        self.curseur.execute(query, data)
        self.connection.commit()
        
        return self.curseur.lastrowid
    
    def get_application(self, id, branch=None, repository=None):
        """Renvoie : l'application correspondante"""
        return Application(self, self.get_application_infos(id, branch, repository))
    
    def get_application_infos(self, id, branch=None, repository=None):
        """Renvoie : les informatons de l'application correspondante"""
        if branch == None:
            if repository == None:
                apps = self.query("SELECT * FROM applications WHERE id = ?"
                                  "ORDER BY version COLLATE desc_versions", (id,))
            else:
                apps = self.query("SELECT * FROM applications WHERE id = ? "
                                  "AND repository = ? "
                                  "ORDER BY version COLLATE desc_versions", (id, repository))
            
            version = apps[0]['version']
            try:
                return dict([i for i in apps if i['branch'] == "Stable" and i['version'] == version][0])
            except IndexError:
                try:
                    return dict([i for i in apps if i['branch'] == "Unstable" and i['version'] == version][0])
                except IndexError:
                    return dict(apps[0])
        else:
            if repository == None:
                apps = self.query("SELECT * FROM applications WHERE id = ? "
                                  "AND branch ? "
                                  "ORDER BY version COLLATE desc_versions", (id, branch))
            else:
                apps = self.query("SELECT * FROM applications WHERE id = ? "
                                  "AND branch = ? "
                                  "AND repository = ? "
                                  "ORDER BY version COLLATE desc_versions", (id, branch, repository))
            return dict(apps[0])
    
    def get_applications(self, category=''):
        """Renvoie : Les applications que contient la catégorie
                     (et ses sous catégories)"""
        applications = self.query("SELECT * FROM applications "
                "WHERE category LIKE ?", (category + "%",))
        return [Application(self, dict(i)) for i in applications]
    
    def get_categories(self):
        """Renvoie : La liste de toutes les catégories"""
        categories = self.query("SELECT id FROM categories")
        return map(lambda (a,):self.get_category(a), categories)
    
    def get_category(self, id):
        """Renvoie : La catégorie correspondante"""
        return Category(self, id)
    
    def get_category_hash(self, id):
        """Renvoie : la somme md5 de l'icône de la catégorie"""
        try:
            return self.query("SELECT hash FROM categories "
                    "WHERE id = ?", (id,))[0][0]
        except IndexError:
            return None
    
    def get_category_icon(self, id):
        """Renvoie : L'icône de la catégorie"""
        hash = self.get_category_hash(id)
        if hash:
            return './cache/icons/' + hash + '.png'
        else:
            return None
    
    def get_config(self, name=None, default=None):      # À modifier (cfg)
		if name == None:
			return self.query("SELECT * FROM config")
		else:
			self.curseur.execute("SELECT * FROM config WHERE name = ?", (name,))
			value = self.curseur.fetchone()
			if value == None:
				return default
			else:
				if value['value'] == None:
					return default
				else:
					if value['value'].isdigit():
						return int(value['value'])
					else:
						return value['value']
    
    def get_depends(self, id, branch, repository):
        """Renvoie : La liste des dépendances de l'application"""
        depends = self.query("SELECT depend FROM depends WHERE application = ? "
                    "AND branch = ? AND repository = ?",
                    (id, branch, repository))
        return map(lambda (a,):a, depends)
    
    def get_icon_hash(self, id, branch, repository, size):
        """Renvoie : la somme md5 de l'icône de l'application"""
        try:
            return self.query("SELECT hash FROM icons WHERE application = ? "
                    "AND branch = ? AND repository = ? AND size = ? ",
                    (id, branch, repository, size))[0]
        except IndexError:
            return None
    
    def get_icons(self, id, branch, repository):
        """Renvoie : Les icônes de l'application"""
        icons = self.query("SELECT size, hash FROM icons WHERE application = ? AND branch = ? AND repository = ?",
                    (id, branch, repository))
        icons = map(lambda (a,b):(a,'./cache/icons/'+b+'.png'), icons)
        return dict(icons)

    def get_installed_application(self, id):
        cfg = ConfigParser({'Show' : 'True', 'InstallDir' : 'Apps', 'ApplicationRoot' : 'Apps/%s' % id})
        cfg.read(['./cache/installed/' + id + '/appinfo.ini', './cache/installed/' + id + '/installer.ini'])
        
        infos = {}
        infos['id'] = id
                
        try:
            infos['branch'] = cfg.get('Framakey', 'Branch')
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
    
    def get_repositories(self):
        """Renvoie : La liste des dépôts"""
        return self.query('SELECT uri, hash FROM repositories')
    
    def get_subcategories(self, id=''):
        """Renvoie : Les sous catégories de la catégorie id"""
        return [i for i in self.get_categories() if get_category_parent(i) == id]
    
    def icon_used(self, hash):
        """Renvoie : True si l'icône est utilisée, False sinon."""
        return self.query('SELECT COUNT(hash) FROM categories WHERE hash = ?', (hash,))[0][0] +  self.query('SELECT COUNT(hash) FROM icons WHERE hash = ?', (hash,))[0][0] > 0
    
    def query(self, query, data=()):
        """Éxecute une commande SQL de type "SELECT"
           Renvoie : les données récupérées"""
        self.curseur.execute(query, data)
        return self.curseur.fetchall()
    
    def remove_all_from_repository(self, uri):
        """Supprime le contenu d'un dépôt"""
        self.execute("DELETE FROM applications WHERE repository = ?", (uri,))
        self.execute("DELETE FROM recommendations WHERE repository = ?", (uri,))
        
        self.execute("DELETE FROM depends WHERE repository = ?", (uri,))
        self.execute("DELETE FROM links WHERE repository = ?", (uri,))
        self.execute("DELETE FROM icons WHERE repository = ?", (uri,))
    
    def remove_category(self, id):
        """Supprime la catégorie id"""
        self.curseur.execute("DELETE FROM categories WHERE id = ?", (id,))
    
    def remove_empty_categories(self):
        """Supprime les catégories vides"""
        for category in self.get_categories():
            if category.count_applications() == 0:
                category.remove()
    
    def remove_old_icons(self):
        """Supprime les icônes inutilisées"""
        for filename in os.listdir("./cache/icons"):
            if not self.icon_used(filename[:-4]):
                os.remove("./cache/icons/" + filename)
        
    def set_config(self, name, value):      # À modifier (cfg)
        self.curseur.execute("SELECT * FROM config WHERE name = ?", (name,))
        if self.curseur.fetchone() == None:
            self.execute("INSERT INTO config (name, value) VALUES (?, ?)", (name, str(value)))
        else:
            self.execute("UPDATE config SET value = ? WHERE name = ?", (str(value), name))
    
    def set_rating(self, id, branch, repository, rating, votes):
        self.execute("UPDATE applications SET rating = ?, votes = ? "
                     "WHERE id = ? AND branch = ? AND repository = ?",
                     (rating, votes, id, branch, repository))
    
    def set_repository_hash(self, uri, hash):
        """Modifie la somme md5 associée à un dépôt"""
        self.curseur.execute("UPDATE repositories SET hash = ? WHERE uri = ?", (hash, uri))
    
    def update(self, force=False):
        """Met à jour la base de donnée"""
        logger.info(u"Mise à jour des dépôts.")
        for repository in self.get_repositories():
            new_hash = urllib2.urlopen(repository['uri'] + '/repository.ini.hash').read()
            if repository['hash'] == new_hash and not force:
                logger.debug(u"Le dépôt %s n'a pas été modifié." % repository['uri'])
            else:
                logger.debug(u"Le dépôt %s a été modifié (ou la mise à jour a été forcée).", repository['uri'])
                self.set_repository_hash(repository['uri'], new_hash)
                
                logger.debug(u"Suppression des anciennes applications du dépôt.")
                self.remove_all_from_repository(repository['uri'])
                
                cfg = get_repository_cfg(repository['uri'])
                
                logger.debug(u"Insertion des recommendations du dépôt.")
                i = 1
                while cfg.has_option('repository', 'recommendation%d'%i):
                    self.add_recommendation(repository['uri'], cfg.get('repository', 'recommendation%d'%i))
                    i += 1
                
                logger.debug(u"Insertion des applications du dépôt.")
                for section in cfg.sections():
                    if section not in ['repository', 'categories', 'categories_hash']:
                        logger.debug(u"Insertion de %s." % section)
                        try:
                            branch, id = tuple(section.split(":", 1))
                            self.add_application(*get_application_cfg_infos(cfg, section, repository['uri']))
                            self.add_category(*get_category_cfg_infos(cfg, cfg.get(section, 'category')))
                            
                            i = 1
                            while cfg.has_option(section, 'link%d'%i):
                                self.add_link(id, branch, repository['uri'], cfg.get(section, 'link%d_name'%i), cfg.get(section, 'link%d'%i))
                                i += 1
                            
                            i = 1
                            while cfg.has_option(section, 'depend%d'%i):
                                self.add_depend(id, branch, repository['uri'], cfg.get(section, 'depend'%i))
                                i += 1
                            
                            for size in [32,48,64,128]:
                                if cfg.has_option(section, 'icon_%d'%size):
                                    self.add_icon(id, branch, repository['uri'], size, cfg.get(section, 'icon_%d'%size), cfg.get(section, 'icon_%d_hash'%size))
                            
                        except (NoSectionError, NoOptionError):
                            logger.warning(u"Les informations de l'application %s du dépôt %s sont incomplète." % (section,repository['uri']))
        
        self.connection.commit()
        
        self.remove_empty_categories()
        self.remove_old_icons()
        
        self.connection.commit()
        logger.info(u"Fin de la mise à jour des dépôts.")
