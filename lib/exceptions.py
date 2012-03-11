#!/usr/bin/python2
# -*- coding: utf-8 -*-

class ApplicationAlreadyInstalled(Exception):
    """Exception levee lorsque l'application à installer est dejà
       installee.

    Attributs:
        application : Classe application
    """
    def __init__(self, application):
        self.application = application
    
    def __str__(self):
        return u"L'application %s est dejà installee." % self.application.id

class InvalidDepends(Exception):
    """Exception levee lorsqu'une application est dans ses propres
       dependances.

    Attributs:
        application : Id de l'application
    """
    def __init__(self, id):
        self.application = id
    
    def __str__(self):
        return u"Les dependances de l'application %s sont invalides." % self.application

class InvalidPackage(Exception):
    """Exception levee lorsqu'il est impossible de lire le contenu d'un
       paquet.

    Attributs:
        application : Classe application
        error       : erreur ayant declenche cette exception
    """
    def __init__(self, application, error):
        self.application = application
        self.error = error
    
    def __str__(self):
        return u"Le paquet %s est invalide." % self.application.id

class InvalidRepository(Exception):
    """Exception levee lorsqu'il est impossible de lire le contenu d'un
       depot.

    Attributs:
        repository : addresse du depot
        error      : erreur ayant declenche cette exception
    """
    def __init__(self, repository, error):
        self.repository = repository
        self.error = error
    
    def __str__(self):
        return u"Le depot %s est invalide." % self.repository

class NonExistingDepends(Exception):
    """Exception levee lorsqu'une application a des dependances
       inexistantes.

    Attributs:
        application : Id de l'application
        depends     : Dependances inexistantes
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
    """Exception levee lorsque l'application recherchee n'existe pas.

    Attributs:
        id         : id de l'application
        branch     : branche de l'application
        repository : depot de l'application
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
    """Exception levee lorsqu'il n'y a pas assez d'espace pour installer
       l'application.

    Attributs:
        space : Espace manquant
    """
    def __init__(self, space):
        self.space = space
    
    def __str__(self):
        return u"Pas assez d'espace disponible (%d octets supplementaires necessaires)." % self.space

class NotEnoughTmpFreeSpace(Exception):
    """Exception levee lorsqu'il n'y a pas assez d'espace telecharger
       les paquets.

    Attributs:
        space : Espace manquant
    """
    def __init__(self, space):
        self.space = space
    
    def __str__(self):
        return u"Pas assez d'espace disponible (%d octets supplementaires necessaires)." % self.space

class PackageDownloadError(Exception):
    """Exception levee lorsque le paquet ne peut pas être telecharge.

    Attributs:
        application : Classe application
        error       : erreur ayant declenche cette exception
    """
    def __init__(self, application, error):
        self.application = application
        self.error = error
    
    def __str__(self):
        return u"Erreur lors du telechargement de l'application %s." % self.application.id
        
class RepositoryConnectionError(Exception):
    """Exception levee lorsqu'il est impossible de se connecter à un
       depot.

    Attributs:
        repository : addresse du depot
        error      : erreur ayant declenche cette exception
    """
    def __init__(self, repository, error):
        self.repository = repository
        self.error = error
    
    def __str__(self):
        return u"Erreur lors de la connection au depot %s." % self.repository
