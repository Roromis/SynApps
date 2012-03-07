#!/usr/bin/python2
# -*- coding: utf-8 -*-

import logging

logger = logging.getLogger('synapps')

import os.path
import sqlite3
import urllib2
import hashlib
from configparser import ConfigParser, NoSectionError, NoOptionError
from distutils import version
from locale import strcoll

def cmp_version(a,b):
    """Compare deux chaînes représentant une version."""
    return -cmp(version.LooseVersion(a), version.LooseVersion(b))

def get_application_infos(cfg, section, repository):
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

def get_category_infos(cfg, category):
    """Récupère les informations sur une catégorie dans le dépôt."""
    if cfg.has_option('categories', category):
        icon_uri = cfg.get('categories', category)
    else:
        icon_uri = ''
        
    if cfg.has_option('categories_hash', category):
        newhash = cfg.get('categories_hash', category)
    else:
        newhash = ''
    return (category, icon_uri, newhash)
    
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
    #try:
    cfg.read_string(tmp.decode('utf-8'))
    #except:
    #    logger.warning(u'Le dépôt %s est invalide' % uri)
    #    raise Exception('Le dépôt %s est invalide' % uri)
    
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
                "id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,"
                "uri TEXT,"
                "hash TEXT DEFAULT '',"
                "show_recommendations BOOL DEFAULT 1,"
                "show_stable BOOL DEFAULT 1,"
                "show_unstable BOOL DEFAULT 1,"
                "show_testing BOOL DEFAULT 1)")
            
            # Recommendations
            self.curseur.execute("CREATE TABLE recommendations ("
                "repository INT,"
                "application TEXT)")
            
            # Catégories
            self.curseur.execute("CREATE TABLE categories ("
                "id TEXT PRIMARY KEY UNIQUE,"
                "hash TEXT)")
            
            # Applications
            self.curseur.execute("CREATE TABLE applications ("
                "id TEXT,"
                "branch TEXT,"
                "repository INT,"
                "category TEXT,"
                "name TEXT,"
                "friendly_name TEXT,"
                "short_description TEXT,"
                "long_description TEXT,"
                "size_c INT,"
                "size_u INT,"
                "version TEXT,"
                "rating INT DEFAULT 0,"
                "votes INT DEFAULT 0,"
                "license TEXT,"
                "author TEXT,"
                "show BOOL,"
                "uri TEXT,"
                "PRIMARY KEY (id, branch, repository))")
            
            # Liens
            self.curseur.execute("CREATE TABLE links ("
                "application TEXT,"
                "branch TEXT,"
                "repository INT,"
                "title TEXT,"
                "uri TEXT)")
            
            # Dépendances
            self.curseur.execute("CREATE TABLE depends ("
                "application TEXT,"
                "branch TEXT,"
                "repository INT,"
                "depend TEXT)")
            
            # Icônes
            self.curseur.execute("CREATE TABLE icons ("
                "application TEXT,"
                "branch TEXT,"
                "repository INT,"
                "size INT,"
                "hash TEXT,"
                "PRIMARY KEY (application, branch, repository, size))")
            
            # Ajout des sources par défaut
            logger.debug(u"Ajout des dépôts Framakey.")
            self.add_repository('http://localhost/fk2')

            # Ajout de la configuration par défaut
            logger.debug(u"Ajout de la configuration par défaut.")
            self.set_config('appspath', '..\Apps')#'..\..\..\..\Apps')
            self.set_config('version', '0.3 alpha 1')
            
            # Exécution
            self.connection.commit()
        else:
            logger.debug(u"Le fichier cache/apps.sqlite existe.")
            self.connection = sqlite3.connect("cache/apps.sqlite")
            self.connection.row_factory = sqlite3.Row
            self.curseur = self.connection.cursor()
        
        # Tri
        self.connection.create_collation("unicode", strcoll)
        self.connection.create_collation("desc_versions", cmp_version)
    
    def add_application(self, id, branch, repository, category, name,
                        friendly_name, short_description,
                        long_description, size_c, size_u, version,
                        license, author, show, uri):
        """Ajoute une application"""
        self.curseur.execute("INSERT INTO applications (id, branch, repository,"
                "category, name, friendly_name, short_description,"
                "long_description, size_c, size_u, version,"
                "license, author, show, uri) VALUES"
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (id, branch, repository,
                category, name, friendly_name, short_description,
                long_description, size_c, size_u, version,
                license, author, show, uri))
    
    def add_category(self, id, icon_uri, newhash):
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
                self.curseur.execute("INSERT INTO categories (id, hash)"
                        "VALUES (?, ?)", (id, newhash))
            else:
                self.curseur.execute("UPDATE categories SET hash = ?"
                        "WHERE id = ?", (newhash, id))
    
    def add_depend(self, id, branch, repository, depend):
        """Ajoute une dépendance"""
        self.curseur.execute("INSERT INTO depends (application, branch, repository, depend)"
                "VALUES (?, ?, ?, ?)", (id, branch, repository, depend))
    
    def add_icon(self, id, branch, repository, size, uri, hash):
        """Ajoute une icône"""
        self.curseur.execute("INSERT INTO icons (application, branch, repository, size, hash)"
                "VALUES (?,?,?,?,?)", (id, branch, repository, size, hash))
        
        if not os.path.isfile('./cache/icons/' + hash + '.png'):
            try:
                with open('./cache/icons/' + hash + '.png', 'wb') as f:
                    f.write(urllib2.urlopen(uri).read())
            except NoOptionError:
                logger.warning(u"Impossible de télécharger l'icône %s." % uri)
    
    def add_link(self, id, branch, repository, title, uri):
        """Ajoute un lien"""
        self.curseur.execute("INSERT INTO links (application, branch, repository, title, uri)"
                "VALUES (?, ?, ?, ?, ?)", (id, branch, repository, title, uri))
    
    def add_recommendation(self, repository, recommendation):
        """Ajoute une recommendation"""
        self.curseur.execute("INSERT INTO recommendations (repository, application)"
                "VALUES (?, ?)", (repository, recommendation))
    
    def add_repository(self, uri):
        """Ajoute un dépôt"""
        self.execute("INSERT INTO repositories (uri) VALUES (?)", (uri,))
    
    def count_apps(self, category):
        """Renvoie : Le nombre d'applications que contient la catégorie
                     (et ses sous catégories)"""
        return self.query("SELECT count(id) FROM applications WHERE category LIKE ?", (category + "%",))[0][0]
        
    def execute(self, query, data=()):
        """Éxecute une commande SQL nécessitant un "commit" (insertion,
           suppression, création de table...)
           Renvoie : l'id de la dernière ligne insérée"""
        self.curseur.execute(query, data)
        self.connection.commit()
        
        return self.curseur.lastrowid
    
    def get_category_hash(self, id):
        """Renvoie : la somme md5 de l'icône de la catégorie"""
        try:
            return self.query("SELECT hash FROM categories WHERE id = ?", (id,))[0][0]
        except IndexError:
            return None
    
    def get_icon_hash(self, id, branch, repository, size):
        """Renvoie : la somme md5 de l'icône de l'application"""
        try:
            return self.query("SELECT hash FROM icons WHERE id = ?"
                              "AND branch = ? AND repository = ? AND size = ? ",
                              (id, branch, repository, size))[0]
        except IndexError:
            return None
    
    def get_repositories(self):
        """Renvoie : La liste des dépôts"""
        return self.query('SELECT id, uri, hash FROM repositories')
    
    def icon_used(self, hash):
        """Renvoie : True si l'icône est utilisée, False sinon."""
        return self.query('SELECT COUNT(hash) FROM categories WHERE hash = ?', (hash,))[0][0] + self.query('SELECT COUNT(hash) FROM icons WHERE hash = ?', (hash,))[0][0] > 0
    
    def query(self, query, data=()):
        """Éxecute une commande SQL de type "SELECT"
           Renvoie : les données récupérées"""
        self.curseur.execute(query, data)
        return self.curseur.fetchall()
    
    def remove_all_from_repository(self, id):
        """Supprime le contenu d'un dépôt"""
        self.execute("DELETE FROM applications WHERE repository = ?", (id,))
        self.execute("DELETE FROM recommendations WHERE repository = ?", (id,))
        
        self.execute("DELETE FROM depends WHERE repository = ?", (id,))
        self.execute("DELETE FROM links WHERE repository = ?", (id,))
        self.execute("DELETE FROM icons WHERE repository = ?", (id,))
    
    def remove_empty_categories(self):
        """Supprime les catégories vides"""
        for cat in self.query("SELECT id FROM categories"):
            if self.count_apps(cat['id']) == 0:
                self.curseur.execute("DELETE FROM categories WHERE id = ?", (cat['id'],))
    
    def remove_old_icons(self):
        """Supprime les icônes inutilisées"""
        for filename in os.listdir("./cache/icons"):
            if not self.icon_used(filename[:-4]):
                os.remove("./cache/icons/" + filename)
        
    def set_config(self, name, value):
        self.curseur.execute("SELECT * FROM config WHERE name = ?", (name,))
        if self.curseur.fetchone() == None:
            self.execute("INSERT INTO config (name, value) VALUES (?, ?)", (name, str(value)))
        else:
            self.execute("UPDATE config SET value = ? WHERE name = ?", (str(value), name))
    
    def set_repository_hash(self, id, hash):
        """Modifie la somme md5 associée à un dépôt"""
        self.curseur.execute("UPDATE repositories SET hash = ? WHERE id = ?", (hash, id))
    
    def update(self, force=False):
        """Met à jour la base de donnée"""
        logger.info(u"Mise à jour des dépôts.")
        for repository in self.get_repositories():
            new_hash = urllib2.urlopen(repository['uri'] + '/repository.ini.hash').read()
            if repository['hash'] == new_hash and not force:
                logger.debug(u"Le dépôt %s n'a pas été modifié." % repository['uri'])
            else:
                logger.debug(u"Le dépôt %s a été modifié (ou la mise à jour a été forcée).", repository['uri'])
                self.set_repository_hash(repository['id'], new_hash)
                
                logger.debug(u"Suppression des anciennes applications du dépôt.")
                self.remove_all_from_repository(repository['id'])
                
                cfg = get_repository_cfg(repository['uri'])
                
                logger.debug(u"Insertion des recommendations du dépôt.")
                i = 1
                while cfg.has_option('repository', 'recommendation%d'%i):
                    self.add_recommendation(repository['id'], cfg.get('repository', 'recommendation%d'%i))
                    i += 1
                
                logger.debug(u"Insertion des applications du dépôt.")
                for section in cfg.sections():
                    if section not in ['repository', 'categories', 'categories_hash']:
                        logger.debug(u"Insertion de %s." % section)
                        try:
                            id, branch = tuple(section.split(":", 1))
                            self.add_application(*get_application_infos(cfg, section, repository['id']))
                            self.add_category(*get_category_infos(cfg, cfg.get(section, 'category')))
                            
                            i = 1
                            while cfg.has_option(section, 'link%d'%i):
                                self.add_link(id, branch, repository['id'], cfg.get(section, 'link%d_name'%i), cfg.get(section, 'link%d'%i))
                                i += 1
                            
                            i = 1
                            while cfg.has_option(section, 'depend%d'%i):
                                self.add_depend(id, branch, repository['id'], cfg.get(section, 'depend'%i))
                                i += 1
                            
                            for size in [32,48,64,128]:
                                if cfg.has_option(section, 'icon_%d'%size):
                                    self.add_icon(id, branch, repository['id'], size, cfg.get(section, 'icon_%d'%size), cfg.get(section, 'icon_%d_hash'%size))
                            
                        except (NoSectionError, NoOptionError):
                            logger.warning(u"Les informations de l'application %s du dépôt %s sont incomplète." % (section,repository['uri']))
        
        self.connection.commit()
        
        self.remove_empty_categories()
        self.remove_old_icons()
        
        self.connection.commit()
