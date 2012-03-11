#!/usr/bin/python2
# -*- coding: utf-8 -*-

class ApplicationAlreadyInstalled(Exception):
    """Exception levée lorsque l'application à installer est déjà
       installée.

    Attributs:
        application : Classe application
    """
    def __init__(self, application):
        self.application = application

class InvalidPackage(Exception):
    """Exception levée lorsqu'il est impossible de lire le contenu d'un
       paquet.

    Attributs:
        application : Classe application
        error       : erreur ayant déclenché cette exception
    """
    def __init__(self, application, error):
        self.application = application
        self.error = error

class InvalidRepository(Exception):
    """Exception levée lorsqu'il est impossible de lire le contenu d'un
       dépôt.

    Attributs:
        repository : addresse du dépôt
        error      : erreur ayant déclenché cette exception
    """
    def __init__(self, repository, error):
        self.repository = repository
        self.error = error

class NoSuchApplication(Exception):
    """Exception levée lorsque l'application recherchée n'existe pas.

    Attributs:
        id         : id de l'application
        branch     : branche de l'application
        repository : dépôt de l'application
    """
    def __init__(self, id, branch, repository):
        self.id = id
        self.branch = branch
        self.repository = repository


class PackageDownloadError(Exception):
    """Exception levée lorsque le paquet ne peut pas être téléchargé.

    Attributs:
        application : Classe application
        error       : erreur ayant déclenché cette exception
    """
    def __init__(self, application, error):
        self.application = application
        self.error = error
        
class RepositoryConnectionError(Exception):
    """Exception levée lorsqu'il est impossible de se connecter à un
       dépôt.

    Attributs:
        repository : addresse du dépôt
        error      : erreur ayant déclenché cette exception
    """
    def __init__(self, repository, error):
        self.repository = repository
        self.error = error
