#!/usr/bin/python2
# -*- coding: utf-8 -*-

import logging
import os.path
import sqlite3
import urllib2
import hashlib
from ConfigParser import ConfigParser
from distutils import version
from locale import strcoll

def cmp_version(a,b):
    return -cmp(version.LooseVersion(a), version.LooseVersion(b))

def md5fp(file):
    hash = hashlib.md5()
    while True:
        data = file.read(128)
        if not data:
            break
        hash.update(data)
    return hash.hexdigest()

class database():
    def __init__(self):
        """Connection à la base de donnée locale des applications"""
        if not os.path.isfile("cache/apps.sqlite"):
            logging.info("Le fichier cache/apps.sqlite n'existe pas "
                         "création de la base de donnée.")
            self.connection = sqlite3.connect("cache/apps.sqlite")
            self.connection.row_factory = sqlite3.Row
            self.curseur = self.connection.cursor()
            
            #  Création des tables
            logging.debug("Création des tables.")
            
            # Configuration
            self.curseur.execute("CREATE TABLE config ("
                "name TEXT PRIMARY KEY UNIQUE,"
                "value TEXT)")
            
            # Dépôts
            self.curseur.execute("CREATE TABLE repositories ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,"
                "name TEXT,"
                "uri TEXT,"
                "hash TEXT,"
                "show_recommendations BOOL)")
            
            # Applications
            self.curseur.execute("CREATE TABLE applications ("
                "id TEXT,"
                "branch TEXT,"
                "repository INT,"
                "name TEXT,"
                "friendly_name TEXT,"
                "short_description TEXT,"
                "long_description TEXT,"
                "size_c INT,"
                "size_u INT,"
                "version TEXT,"
                "mark INT,"
                "votes INT,"
                "license TEXT,"
                "author TEXT,"
                "show BOOL,"
                "uri TEXT,"
                "PRIMARY KEY (id, branch))")
            
            # Liens
            self.curseur.execute("CREATE TABLE links ("
                "application TEXT,"
                "title TEXT UNIQUE,"
                "uri TEXT)")
            
            # Dépendances
            self.curseur.execute("CREATE TABLE depends ("
                "application TEXT,"
                "depend TEXT)")
            
            # Icônes
            self.curseur.execute("CREATE TABLE icons ("
                "application TEXT,"
                "size INT,"
                "file BLOB,"
                "hash TEXT,"
                "PRIMARY KEY (application, size))")
            
            # Recommendations
            self.curseur.execute("CREATE TABLE recommendations ("
                "repository INT,"
                "application TEXT)")
            
            # Ajout des sources par défaut
            logging.debug("Ajout des dépôts Framakey.")
            #self.execute("INSERT INTO repositories"
            #        "(id, name, uri, hash) VALUES (0,'Local','','')")
            self.add_repository('http://localhost/fk2')

            # Ajout de la configuration par défaut
            logging.debug("Ajout de la configuration par défaut.")
            self.set_config('appspath', '..\Apps')#'..\..\..\..\Apps')
            self.set_config('version', '0.3 alpha 1')
            
            # Exécution
            self.connection.commit()
        else:
            logging.debug("Le fichier cache/apps.sqlite existe.")
            self.connection = sqlite3.connect("cache/apps.sqlite")
            self.connection.row_factory = sqlite3.Row
            self.curseur = self.connection.cursor()
        
        # Tri
        self.connection.create_collation("unicode", strcoll)
        self.connection.create_collation("desc_versions", cmp_version)
    
    def add_repository(self, uri):
        # Téléchargement du dépôt
        try:
            tmp = urllib2.urlopen(uri + '/repository.ini')
        except:
            logging.warning('Impossible de se connecter au dépôt %s' % uri)
            raise Exception('Impossible de se connecter au dépôt %s' % uri)
        
        # Lecture du dépôt
        cfg = ConfigParser()
        cfg.readfp(tmp)
        
        try:
            name = cfg.get('repository', 'name')
        except:
            logging.warning('Le dépôt %s est invalide' % uri)
            raise Exception('Le dépôt %s est invalide' % uri)
        
        self.execute("INSERT INTO repositories"
            "(name, uri, hash       , show_recommendations) VALUES (?, ?, ?, ?)",
             (name, uri, md5fp(tmp) , True))
        
    def execute(self, query, data=()):
        self.curseur.execute(query, data)
        self.connection.commit()
        
        return self.curseur.lastrowid
        
    def query(self, query, data=()):
        self.curseur.execute(query, data)
        return self.curseur.fetchall()
        
    def set_config(self, name, value):
        self.curseur.execute("SELECT * FROM config WHERE name = ?", (name,))
        if self.curseur.fetchone() == None:
            self.execute("INSERT INTO config (name, value) VALUES (?, ?)", (name, str(value)))
        else:
            self.execute("UPDATE config SET value = ? WHERE name = ?", (str(value), name))
