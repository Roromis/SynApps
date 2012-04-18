#!/usr/bin/python2
# -*- coding: utf-8 -*-

from collections import deque
from functools import partial

from exceptions import *

class OperationsQueue(deque):
    """File d'attente (FIFO) contenant les opérations à effectuer."""
    def __init__(self):
        self.current_operation = None
        self.current_progress = 0
        
        deque.__init__(self)
        
        # Dictionnaire contenant les callbacks globaux
        self.callbacks = self.get_default_callbacks()
    
    def add_callback(self, operation, event, callback):
        """
            Ajoute un callback global (exécuté pour toutes les applications)
           
            Arguments :
                operation : opération ('install', 'uninstall' ou 'upgrade')
                event : évenement ('start', 'progress' ou 'end')
                callback : fonction de signature
                    si event vaut 'start' ou 'end' : def callback(app)
                    sinon : def callback(app, progress, message)
        """
        self.callbacks[operation][event].append(callback)
    
    def remove_callback(self, operation, event, callback):
        """
            Supprime un callback global
           
            Arguments :
                operation : opération ('install', 'uninstall' ou 'upgrade')
                event : évenement ('start', 'progress' ou 'end')
                callback : fonction de signature
                    si event vaut 'start' ou 'end' : def callback(app)
                    sinon : def callback(app, progress, message)
        """
        self.callbacks[operation][event].remove(callback)
    
    def append(self, operation):
        """
            Ajoute une opération à la file d'attente
        
            Arguments :
                operation : dictionnaire décrivant l'opération
                    operation['type'] : type d'opération ('install',
                                             'uninstall' ou 'upgrade')
                    operation['application'] : application concernée
                    operation['callbacks'][event] : liste de fonctions à
                                                    appeler à l'évenement event
        """
        if not self.contains_operation(operation):
            # Si l'opération n'est pas déjà dans la queue
            if self.contains_application(operation['application'].id):
                # Si la même application est dans la queue pour une autre
                # opération
                raise ApplicationAlreadyInQueue(operation['application'])
            
            deque.append(self, operation)
            
            if self.current_operation == None:
                # On exécute l'opération si aucune autre opération n'est en cours
                # TODO : à faire dans un thread
                self.next_operation()
    
    def append_install(self, application, callbacks):
        """
            Ajoute l'installation d'une application à la file d'attente
        
            Arguments :
                application : Classe Application
                callbacks[event] : liste de fonctions à appeler à l'évenement
                                   event
        """
        if not application.is_installed():
            self.append({
                            'application' : application,
                            'type' : 'install',
                            'callbacks' : callbacks
                        })
    
    def append_uninstall(self, application, callbacks):
        """
            Ajoute la désinstallation d'une application à la file d'attente
        
            Arguments :
                application : Classe Application
                callbacks[event] : liste de fonctions à appeler à l'évenement
                                   event
        """
        if application.is_installed():
            self.append({
                            'application' : application,
                            'type' : 'uninstall',
                            'callbacks' : callbacks
                        })
    
    def append_upgrade(self, application, callbacks):
        """
            Ajoute la mise à jour d'une application à la file d'attente
        
            Arguments :
                application : Classe Application
                callbacks[event] : liste de fonctions à appeler à l'évenement
                                   event
        """
        if not application.is_up_to_date():
            self.append({
                            'application' : application,
                            'type' : 'upgrade',
                            'callbacks' : callbacks
                        })
    
    def contains_application(self, id):
        """
            Renvoie :
                True si l'application est dans la file d'attente,
                False sinon
        
            Arguments :
                id : identifiant de l'application
        """
        if self.current_operation != None:
            if self.current_operation['application'].id == id:
                # L'application est en train d'être installée, désinstallée ou
                # mise à jour
                return True
        
        for operation in self:
            if operation['application'].id == id:
                # L'application est dans la file d'attente
                return True
        return False
    
    def contains_operation(self, operation):
        """
            Renvoie :
                True si l'operation est dans la file d'attente,
                False sinon
        
            Arguments :
                operation : Operation
        """
        if self.current_operation != None:
            if self.current_operation['application'].id == operation['application'].id \
                and self.current_operation['type'] == operation['type']:
                # L'application est en train d'être installée, désinstallée ou
                # mise à jour
                return True
        
        for queued_operation in self:
            if queued_operation['application'].id == operation['application'].id \
                and queued_operation['type'] == operation['type']:
                # L'application est dans la file d'attente
                return True
        return False
    
    def get_default_callbacks(self):
        """
            Renvoie : la structure du dictionnaire contenant les callbacks
        """
        return {
            'install' : {
                    'start' : [],
                    'progress' : [],
                    'end' : []
                },
            'uninstall' : {
                    'start' : [],
                    'progress' : [],
                    'end' : []
                },
            'upgrade' : {
                    'start' : [],
                    'progress' : [],
                    'end' : []
                }
            }
    
    def next_operation(self):
        """
            Effectue les opérations suivantes
            
            Renvoie : None quand il n'y a plus d'opérations à effectuer
        """
        try:
            # Récupère la prochaine opération (premier élément inséré dans la
            # file)
            operation = self.popleft()
        except IndexError:
            return None
        
        # Modifie l'opération courante
        self.current_operation = operation
        self.current_progress = 0
        
        # Appelle le callback de début
        self.run_callbacks(operation, 'start')
        
        # callback(...) = self.run_callbacks(operation, 'progress', ...)
        callback = partial(self.run_callbacks, operation, 'progress')
        
        if operation['type'] == "install":
            operation['application']._install(callback)
        if operation['type'] == "uninstall":
            operation['application']._uninstall(callback)
        
        self.current_operation = None
        self.current_progress = 0
        
        # Appelle le callback de fin
        self.run_callbacks(operation, 'end')
        
        self.next_operation()
    
    def run_callbacks(self, operation, event, progress=0, message=''):
        """
            Lance les fonctions callbacks
            
            Argument :
                operation : opération
                progress : Progression (en pourcents) (si event vaut 'progress')
                message : Message (si event vaut 'progress')
        """
        if event == 'progress':
            args = (operation['application'], progress, message)
        else:
            args = (operation['application'],)
        
        try:
            c = self.callbacks[operation['type']][event]
        except KeyError:
            c = []
        for f in c:
            f(*args)
        
        try:
            c = operation['callbacks'][event]
        except KeyError:
            c = []
        for f in c:
            f(*args)
