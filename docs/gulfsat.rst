.. _dvbboxes_gulfsat:

====================
Installation Gulfsat
====================

Dans l'infrastructure Gulfsat, dvbboxes est installé sur le conteneur :code:`dektec.malagasy.com` en tant que paquet pip, pour l'utilisateur dvb uniquement.

La configuration est dans :file:`/etc/dvbboxes/configuration` et organise le cluster :code:`dvbbox` par villes.

Chaque instance REDIS sur chaque installation de :code:`dvbbox` a une instance esclave sur :code:`dektec.malagasy.com`.
Les configurations de ces instances esclaves sont dans :file:`/etc/redis/<nom_hote>.conf`.
Les scripts de lancement de ces instances esclaves sont dans :file:`/etc/init.d/redis-server-<nom_hote>`.
