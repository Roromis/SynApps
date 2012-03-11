#!/usr/bin/python2
# -*- coding: utf-8 -*-

from exceptions import *

class DependencyTree(object):
    def __init__(self, database, root, path=[]):
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
    
    def display(self, indent=0):
        """Affiche l'arbre des dépendances (pour débugger)"""
        print indent*"   "  + self.root.id
        for i in self.children:
            i.display(indent+1)
    
    def get_size(self, depends=[]):
        """Renvoie : la liste des dépendances à installer, l'espace nécessaire
                     dans le dossier temporaire et l'espace nécessaire sur la
                     clé"""
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
