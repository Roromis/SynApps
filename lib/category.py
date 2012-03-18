#!/usr/bin/python2
# -*- coding: utf-8 -*-

import logging

logger = logging.getLogger('synapps')

class Category(object):
    def __init__(self, database, id):
        """
            Initialisation : récupération de l'icône dans la base de donnée
            
            Arguments :
                database : Base de donnée
                id : Identifiant de la catégorie
        """
        self.database = database
        self.id = id
        self.icon = database.get_category_icon(self.id)
    
    def count_applications(self):
        """
            Renvoie : Le nombre d'applications que contient la catégorie
        """
        return self.database.count_applications(self.id)
    
    def get_subcategories(self):
        """
            Renvoie : Les sous catégories
        """
        return self.database.get_subcategories(self.id)
    
    def get_applications(self):
        """
            Renvoie : Les applications que contient la catégorie (et ses sous
                      catégories)
        """
        return self.database.get_applications(self.id)
    
    def remove(self):
        """
            Supprime la catégorie
        """
        self.database.remove_category(self.id)
