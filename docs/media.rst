.. _dvbboxes_media:

===================================================
Gestion des fichiers media (:code:`dvbboxes.Media`)
===================================================

Chaque instance de :code:`dvbbox` maintient à jour une base de données REDIS (db=1)
où elle stock les fichiers media présents sur les disques de son hôte ainsi que leurs durées.

:code:`dvbboxes` utilise ces informations pour créer un objet :code:`Media` qui va contenir
les informations suivantes:

* :code:`name`: le nom du fichier media
* :code:`towns`: la liste des villes où le fichier media est présent (un :code:`set()` en python)
* :code:`duration`: la durée en secondes du fichier (le maximum de toutes les durées rencontrées)

.. note::

   A l'initialisation, la classe :code:`Media` va stocker la durée du fichier dans la base
   de données REDIS locale de :code:`dvbboxes` (db=1).

Rechercher un fichier
=====================

La recherche d'un fichier à travers le cluster, se fait via la méthode statique :code:`search()`
de la classe :code:`dvbboxes.Media`.

La méthode a juste besoin d'une expression et d'un nom, ou d'une liste de noms, de villes
dans lequelles chercher.

.. code-block:: python

   >>> Media.search("something_to_search", towns=None)  # par défaut toutes les villes

Elle retourne une liste triée des noms de fichiers correspondant à la recherche.

Emploi du temps
===============

La classe :code:`Media` propose aussi la possibilité de rechercher les dates et heures
de diffusion d'un fichier media.

.. code-block:: python

   >>> Media("my_movie").schedule

Le résultat est un dictionnaire dont les clés sont les identifiants des chaines
sur le réseau TNT et les valeurs sont les timestamps auxquels le fichier est censé
être diffusé
