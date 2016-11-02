.. _dvbboxes_programs:

=================================================
Gestion des programmes (:code:`dvbboxes.Program`)
=================================================

L'application propose aussi un guide des programmes tout simple.

Suivant un jour donné, un numéro de chaine, :code:`dvbboxes` est à même de fournir
la liste des fichiers prévus pour diffusion ainsi que leurs heures exactes de début.

Sachant que :code:`dvbboxes` traverse tout ou partie du cluster, le programme le plus
pertinent est celui qui comporte le plus de fichiers à diffuser et qui se termine le plus tard
(entre minuit et 07h29 le lendemain).

.. code-block:: python

   >>> Program('jjmmaaaa', 'service_id').infos(towns=None)

