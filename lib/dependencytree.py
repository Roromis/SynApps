#!/usr/bin/python2
# -*- coding: utf-8 -*-

from exceptions import *

class DependencyTree(object):
    """Arbre des dépendances d'une application"""
    def __init__(self, database, root, path=[]):
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
        for d in root.depends:
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
                        self.children.append(DependencyTree(database, app, path[:]))
                    except NonExistingDepends as e:
                        for i in e.depends:
                            if i not in nonexisting_depends:
                                nonexisting_depends.append(i)
        
        if len(nonexisting_depends) > 0:
            raise NonExistingDepends(root.id, nonexisting_depends)
    
    def get_size(self, depends=[]):
        """
            Arguments :
                depends : liste des dépendances dont la taille a déjà été prise
                          en compte (utilisé lors de l'appel récursif)
            
            Renvoie : (depends, size_c, size_u)
                depends : liste des dépendances à installer
                size_c : espace nécessaire dans le dossier temporaire
                size_u : espace nécessaire dans le dossier des applications
        """
        if self.root.id not in depends and not self.root.is_installed():
            depends.append(self.root.id)
            
            size_c = self.root.size_c
            size_u = self.root.size_u
            
            for child in self.children:
                depends, newsize_c, newsize_u = child.get_size(depends)
                
                # Les paquets sont supprimés à la fin de leur installation : il
                # n'y en a qu'un à la fois dans le dossier temporaire
                size_c = max(size_c, newsize_c)
                
                size_u += newsize_u
                
            return depends, size_c, size_u
        else:
            return depends, 0, 0
    
    def install(self, callbacks={}):
        """Installe les dépendances, puis la racine (parcours postfixe)"""
        
        for child in self.children:
            child.install()
        
        self.database.operations_queue.append_install(self.root, callbacks)
