#!/usr/bin/python2
# -*- coding: utf-8 -*-

import logging

logger = logging.getLogger('synapps')

class Category(object):
    def __init__(self, database, infos):
        """
            Initialisation : récupération de l'icône dans la base de donnée
            
            Arguments :
                database : Base de donnée
                infos : dictionnaire contenant les informations de
                        la catégorie
                    infos['id'] : Identifiant de la catégorie
                    infos['icon'] : Icône de la catégorie
        """
        self.database = database
        self.infos = infos
    
    def __getattr__(self, name):
        """
            Permet de renvoyer l'information name si l'attribut n'existe pas.
            Par exemple self.id vaut self.infos['id']
        """
        return self.infos[name]
    
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
