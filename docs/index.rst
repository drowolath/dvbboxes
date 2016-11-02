.. _dvbboxes:

========
dvbboxes
========

:code:`dvbboxes` est une application qui tente d'autoriser la gestion de plusieurs instances de :code:`dvbbox`.

L'idée est de grouper les instances par réseau/ville/ce que vous voulez. Chaque groupe est aussi considéré comme un cluster.


Pré-requis
==========

Pour fonctionner, dvbboxes a besoin de:

* python 2.7
* redis>=2.10
* Flask>=0.10
* Flask-Script>=0.6

Configuration
=============

En tant qu'aggrégateur, :code:`dvbboxes` a besoin de configurations assez lourdes.

Instances REDIS esclaves
------------------------

:code:`dvbbox` repose sur REDIS pour stocker les infos relatives:

* aux programmes de diffusions
* aux durées des fichiers media présents sur le disque

Sur chaque instance de dvbbox, REDIS est configuré pour être accessible à distance.

:code:`dvbboxes` va donc se connecter à chacune des bases de données REDIS du cluster en créant des instances REDIS locales,
chacune étant esclave d'une et d'une seule instance REDIS du cluster.

Pour celà, il faut créer des fichiers de configuration dans :file:`/etc/redis` précisant clairement quel serveur est le maître,
et sur quel port local on veut déployer l'esclave.
      

/etc/dvbboxes/configuration
---------------------------

Ce fichier contient les différentes informations sur le cluster à gérer, l'emplacement des fichiers de logs, des données vitale, etc.

.. code-block:: INI

   [LOG]
   filepath=/tmp/dvbboxes.log
   level=10
   datefmt=%d-%m-%Y %H:%M:%S

   [DATA]
   folder=/var/tmp/dvbboxes

   [CHANNELS]
   1=ma chaine
   2=ta chaine

   [CLUSTER:nom]
   fqdn_1=port_redis_esclave_fqdn_1
   fqdn_2=port_redis_esclave_fqdn_2


Les informations précisées dans l'exemple ci-dessus sont les informations obligatoires.
Si un fichier ou répertoire utilisé dans la configuration n'existe pas, il faut le créer.

Installation
============

.. code-block:: bash

   $ git clone http://gitlab.blueline.mg/default/dvbboxes.git -b master
   $ cd dvbboxes
   $ make
   $ sudo make install


dvbboxes est maintenant installé et le binaire :file:`/usr/bin/dvbboxes` est mis à disposition en tant qu'interface CLI

Documentation
=============

.. toctree::
   :maxdepth: 4
   :glob:

   *

