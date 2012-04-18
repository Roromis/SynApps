#!/usr/bin/python2
# -*- coding: utf-8 -*-

from exceptions import *

class DependencyTree(object):
    """Arbre des dépendances d'une application"""
    def __init__(self, database, root, reverse=False, path=[]):
        """
            Arguments :
                database : Base de donnée des applications
                root : Application à la racine de l'arbre
                path : Liste représentant le chemin parcouru pour accéder à
                       l'application (path[i+1] est une dépendance de path[i])
        """
        self.database = database
        
        path.append(root.id)
        
        self.root = root
        self.children = []
        
        nonexisting_depends = []
        
        if reverse:
            l = root.provides
        else:
            l = root.depends
        
        for d in l:
            if d in path:
                # Il y a une boucle dans l'arbre des dépendances
                raise InvalidDepends(d)
            else:
                try:
                    app = database.get_application(d)
                except NoSuchApplication:
                    # L'application n'existe pas
                    nonexisting_depends.append(d)
                else:
                    try:
                        # "path[:]" permet d'envoyer une copie de path (et non
                        # un référence)
                        self.children.append(DependencyTree(database, app, reverse, path[:]))
                    except NonExistingDepends as e:
                        for i in e.depends:
                            if i not in nonexisting_depends:
                                nonexisting_depends.append(i)
        
        if len(nonexisting_depends) > 0:
            raise NonExistingDepends(root.id, nonexisting_depends)
    
    def _print(self, indent=0):
        """
            Affice l'arbre (debuggage)
        """
        print "   "*indent + self.root.id
        for i in self.children:
            i._print(indent + 1)
    
    def get_installed(self):
        """
            Renvoie : la liste des applications installées de l'arbre distinctes
                      de la racine
        """
        return [i for i in self.to_list() if i.is_installed() and i != self.root]
    
    def get_size(self, installed=False):
        """
            Arguments :
                installed : état des applications à prendre en compte
            
            Renvoie : (size_c, size_u)
                size_c : espace nécessaire dans le dossier temporaire
                size_u : espace nécessaire dans le dossier des applications
        """
        size_c = 0
        size_u = 0
        
        for application in self.to_list():
            if application.is_installed() == installed:
                size_c = max(size_c, application.size_c)
                size_u += application.size_u
            
        return size_c, size_u
    
    def install(self, callbacks={}):
        """Installe les dépendances, puis la racine (parcours postfixe)"""
        
        if not self.root.is_installed():
            for child in self.children:
                child.install()
            
            self.database.operations_queue.append_install(self.root, callbacks)
    
    def to_list(self, l=[]):
        if not self.root in l:
            l.append(self.root)
            for child in self.children:
                l = child.to_list(l)
        return l
    
    def uninstall(self, callbacks={}):
        """
            Désinstalle les applications fournies, puis la racine (parcours
            postfixe)
        """
        
        if self.root.is_installed():
            for child in self.children:
                child.uninstall()
            
            self.database.operations_queue.append_uninstall(self.root, callbacks)
