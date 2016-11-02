.. _dvbboxes_listing:

===============================================
Gestion des listings (:code:`dvbboxes.Listing`)
===============================================

Le listing c'est ce que :code:`dvbbox` utilise pour créer des listes de lecture, des programmes.

Un listing ça ressemble à ça:

.. code-block:: bash

   [01/01]
   fichier_0
   fichier_1
   fichier_2
   fichier_3
   fichier_4
		
   [02/01]
   un_autre_fichier_0
   un_autre_fichier_1
   un_autre_fichier_2
   un_autre_fichier_3
   un_autre_fichier_4

Créer un listing est de la responsabilité de la personne qui veut créer des programmes.
En d'autres termes, l'ordre dans lequel on liste les fichiers à diffuser pour un jour donné,
est important et doit être vérifié à l'édition.

Analyse d'un listing
====================

Lorsqu'un listing est créé, on a bien envie de savoir ce qu'il peut produire comme programmes de diffusion.
Ceci afin de savoir si les programmes sont cohérents et finissent à des heures raisonnables.

Quand on initialise la classe :code:`dvbboxes.Listing` on fournit le chemin complet du fichier de listing.
Avec cette information, un objet avec les informations suivantes est créé:

* :code:`filenames`: un dictionnaire dont les clés sont les fichiers inscrits dans le listing
et les valeurs leurs durées respectives en secondes.
* :code:`days`: la liste des jours inscrits dans le listing

Une méthode intuitive est alors proposée: :code:`parse()`.

.. code-block:: python

   >>> Listing('/path/to/my/listing').parse()

Elle retourne un générateur qui renvoie à chaque itération la représentation JSON
d'un dictionnaire dont les clés sont les heures de début (indexées) et les valeurs les 
noms des fichiers concernés. Le même dictionnaire contient une clé **day** qui fait
référence à la date traitée.

Application d'un listing
========================

Dans le jargon de :code:`dvbboxes`, appliquer un listing, revient à écrire le programme de chaque jour (inscrit dans le listing) dans chaque base de données REDIS du cluster.

A cet effet, une méthode statique est proposée:

.. code-block:: python

   >>> Listing.apply(parsed_data, service_id, towns='antananarivo')

Dans cette méthode, **parsed_data** est un itérable qui contient des dictionnaires
dont les clés sont les heures de début (indexées) et les valeurs les 
noms des fichiers concernés. Chaque dictionnaire contient une clé **day** qui fait
référence à la date traitée.

Il y a autant de dictionnaire que de jours inscrits dans le listing.

La méthode retourne un dictionnaire qui indique pour chaque ville, chaque jour, chaque serveur
si les opérations de suppression d'informations obsolètes (delete) ainsi que celles d'insertion
de nouvelles informations (insert) se sont bien déroulées.
