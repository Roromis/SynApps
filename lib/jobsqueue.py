#!/usr/bin/python2
# -*- coding: utf-8 -*-

from collections import deque

from exceptions import *

class JobsQueue(deque):
    """File d'attente (FIFO) contenant les opérations à effectuer."""
    def __init__(self):
        self.current_job = None
        
        deque.__init__(self)
    
    def _append(self, job):
        """
            Ajoute une opération à la file d'attente
        
            Arguments :
                job : dictionnaire
                    job['application'] : application concernée
                    job['type'] : type d'opération ('install', 'uninstall'
                                  ou 'upgrade')
                    job['kwargs'] : arguments supplémentaire
                    job['callback'] : fonction
        """
        if not self.contains_job(job):
            # Si l'opération n'est pas déjà dans la queue
            if self.contains_application(job['application'].id):
                # Si la même application est dans la queue pour une autre
                # opération
                raise ApplicationAlreadyInQueue(job['application'])
            
            self.append(job)
            
            self.start()
    
    def append_install(self, application, callback=None, **kwargs):
        """
            Ajoute l'installation d'une application à la file d'attente
        
            Arguments :
                application : Classe Application
                callback : fonction
        """
        if not application.is_installed():
            self._append({
                'application' : application,
                'type' : 'install',
                'callback' : callback,
                'kwargs' : kwargs
                })
    
    def append_uninstall(self, application, callback=None, **kwargs):
        """
            Ajoute la désinstallation d'une application à la file d'attente
        
            Arguments :
                application : Classe Application
                callback : fonction
        """
        if application.is_installed():
            self._append({
                'application' : application,
                'type' : 'uninstall',
                'callback' : callback,
                'kwargs' : kwargs
                })
    
    def append_upgrade(self, application, callback=None, **kwargs):
        """
            Ajoute la mise à jour d'une application à la file d'attente
        
            Arguments :
                application : Classe Application
                callback : fonction
        """
        if application.is_installed() and not application.is_up_to_date():
            self._append({
                'application' : application,
                'type' : 'upgrade',
                'callback' : callback,
                'kwargs' : kwargs
                })
    
    def contains_application(self, id):
        """
            Renvoie :
                True si l'application est dans la file d'attente,
                False sinon
        
            Arguments :
                id : identifiant de l'application
        """
        if self.current_job != None:
            if self.current_job['application'].id == id:
                # L'application est en train d'être installée, désinstallée ou
                # mise à jour
                return True
        
        for job in self:
            if job['application'].id == id:
                # L'application est dans la file d'attente
                return True
        return False
    
    def contains_job(self, job):
        """
            Renvoie :
                True si l'opération est dans la file d'attente,
                False sinon
        
            Arguments :
                job : opération
        """
        if self.current_job != None:
            if self.current_job['application'].id == job['application'].id \
                and self.current_job['type'] == job['type']:
                # L'opération est en cours
                return True
        
        for queued_job in self:
            if queued_job['application'].id == job['application'].id \
                and queued_job['type'] == job['type']:
                # L'opération est dans la file d'attente
                return True
        return False
    
    def next_job(self):
        """
            Effectue les opérations suivantes
            
            Renvoie : None quand il n'y a plus d'opérations à effectuer
        """
        try:
            # Récupère la prochaine opération (premier élément inséré dans la
            # file)
            job = self.popleft()
        except IndexError:
            return None
        
        # Modifie l'opération courante
        self.current_job = job
        
        if job['type'] == "install":
            job['application']._install(job['callback'], **job['kwargs'])
        if job['type'] == "uninstall":
            job['application']._uninstall(job['callback'], **job['kwargs'])
        
        self.current_job = None
        
        self.next_job()

    def start(self):
        """
            Lance les opérations (si aucune n'est en cours)
        """
        if self.current_job == None:
            # On exécute l'opération si aucune autre opération n'est en cours
            self.next_job()
