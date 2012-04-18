#!/usr/bin/python2
# -*- coding: utf-8 -*-

class ApplicationAlreadyInstalled(Exception):
    """
        Exception levée lorsque l'application à installer est déjà installée.

        Attributs:
            application : Classe application
    """
    def __init__(self, application):
        self.application = application
    
    def __str__(self):
        return u"L'application %s est deja installee." % self.application.id

class ApplicationAlreadyInQueue(Exception):
    """
        Exception levée lorsque l'application est déjà dans la queue

        Attributs:
            application : Classe application
    """
    def __init__(self, application):
        self.application = application
    
    def __str__(self):
        return u"L'application %s est deja dans la queue." % self.application.id

class ApplicationNeeded(Exception):
    """
        Exception levée lorsqu'une application est désinstallée alors que des
        applications fournies sont installées

        Attributs:
            application : Id de l'application
            provides : Applications fournies
    """
    def __init__(self, id, provides):
        self.application = id
        self.provides = provides
    
    def str_of_list(self):
        if len(self.provides) == 1:
            return self.provides[0]
        else:
            return u', '.join(self.provides[:-1]) + u' et ' + self.provides[-1]
    
    def __str__(self):
        return u"Les applications %s dépendent de l'application %s." % (self.str_of_list(), self.application)

class ApplicationNotInstalled(Exception):
    """
        Exception levée lorsque l'application à désinstaller n'est pas installée

        Attributs:
            application : Classe application
    """
    def __init__(self, application):
        self.application = application
    
    def __str__(self):
        return u"L'application %s n'est pas installee." % self.application.id

class InvalidDepends(Exception):
    """
        Exception levée lorsqu'une application est dans ses propres dépendances.

        Attributs:
            application : Id de l'application
    """
    def __init__(self, id):
        self.application = id
    
    def __str__(self):
        return u"Les dependances de l'application %s sont invalides." % self.application

class InvalidPackage(Exception):
    """
        Exception levée lorsqu'il est impossible de lire le contenu d'un paquet.

        Attributs:
            application : Classe application
            error : Erreur ayant declenché cette exception
    """
    def __init__(self, application, error):
        self.application = application
        self.error = error
    
    def __str__(self):
        return u"Le paquet %s est invalide." % self.application.id

class InvalidRepository(Exception):
    """
        Exception levée lorsqu'il est impossible de lire le contenu d'un dépôt.

        Attributs:
            repository : addresse du depot
            error : Erreur ayant declenché cette exception
    """
    def __init__(self, repository, error):
        self.repository = repository
        self.error = error
    
    def __str__(self):
        return u"Le depot %s est invalide." % self.repository

class NonExistingDepends(Exception):
    """
        Exception levée lorsqu'une application a des dépendances inexistantes.

        Attributs:
            application : Id de l'application
            depends : Dépendances inexistantes
    """
    def __init__(self, id, depends):
        self.application = id
        self.depends = depends
    
    def str_of_list(self):
        if len(self.depends) == 1:
            return self.depends[0]
        else:
            return u', '.join(self.depends[:-1]) + u' et ' + self.depends[-1]
    
    def __str__(self):
        return u"Les dependances %s de l'application %s sont introuvables." % (self.str_of_list(), self.application)

class NoSuchApplication(Exception):
    """
        Exception levée lorsque l'application recherchée n'existe pas.

        Attributs:
            id         : Identifiant de l'application
            branch     : Branche de l'application
            repository : Dépôt de l'application
    """
    def __init__(self, id, branch, repository):
        self.id = id
        self.branch = branch
        self.repository = repository
    
    def __str__(self):
        if self.branch == None:
            branch = u''
        else:
            branch = self.branch + u":"
        
        if self.repository == None:
            repository = u"les depots."
        else:
            repository = u"le depot %s."
        
        return u"L'application %s%s n'est pas presente dans %s" % (branch, self.id, repository)

class NotEnoughRootFreeSpace(Exception):
    """
        Exception levée lorsqu'il n'y a pas assez d'espace pour installer
        l'application.

        Attributs:
            space : Espace manquant
    """
    def __init__(self, space):
        self.space = space
    
    def __str__(self):
        return u"Pas assez d'espace disponible (%d octets supplementaires necessaires)." % self.space

class NotEnoughTmpFreeSpace(Exception):
    """
        Exception levée lorsqu'il n'y a pas assez d'espace télécharger les
        paquets.

        Attributs:
            space : Espace manquant
    """
    def __init__(self, space):
        self.space = space
    
    def __str__(self):
        return u"Pas assez d'espace disponible (%d octets supplementaires necessaires)." % self.space

class PackageDownloadError(Exception):
    """
        Exception levée lorsque le paquet ne peut pas être téléchargé.

        Attributs:
            application : Classe application
            error : Erreur ayant déclenché cette exception
    """
    def __init__(self, application, error):
        self.application = application
        self.error = error
    
    def __str__(self):
        return u"Erreur lors du telechargement de l'application %s." % self.application.id
        
class RepositoryConnectionError(Exception):
    """
        Exception levée lorsqu'il est impossible de se connecter à un dépôt.

    Attributs:
        repository : Adresse du dépôt
        error : Erreur ayant déclenché cette exception
    """
    def __init__(self, repository, error):
        self.repository = repository
        self.error = error
    
    def __str__(self):
        return u"Erreur lors de la connection au depot %s." % self.repository
