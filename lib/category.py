#!/usr/bin/python2
# -*- coding: utf-8 -*-

class Category(object):
    def __init__(self, database, id):
        """Initialisation : récupération de l'icône dans la base de
           donnée"""
        self.database = database
        self.id = id
        self.icon = database.get_category_icon(self.id)
    
    def count_applications(self):
        return self.database.count_applications(self.id)
    
    def get_subcategories(self):
        return self.database.get_subcategories(self.id)
    
    def get_applications(self):
        return self.database.get_applications(self.id)
    
    def remove(self):
        self.database.remove_category(self.id)
