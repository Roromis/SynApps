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

class InvalidDepends(Exception):
    """Exception levée lorsqu'une application est dans ses propres
       dépendances.

    Attributs:
        application : Id de l'application
    """
    def __init__(self, id):
        self.application = id

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

class NonExistingDepends(Exception):
    """Exception levée lorsqu'une application a des dépendances
       inexistantes.

    Attributs:
        application : Id de l'application
        depends     : Dépendances inexistantes
    """
    def __init__(self, id, depends):
        self.application = id
        self.depends = depends

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

class NotEnoughRootFreeSpace(Exception):
    """Exception levée lorsqu'il n'y a pas assez d'espace pour installer
       l'application.

    Attributs:
        space : Espace manquant
    """
    def __init__(self, space):
        self.space = space

class NotEnoughTmpFreeSpace(Exception):
    """Exception levée lorsqu'il n'y a pas assez d'espace télécharger
       les paquets.

    Attributs:
        space : Espace manquant
    """
    def __init__(self, space):
        self.space = space

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
