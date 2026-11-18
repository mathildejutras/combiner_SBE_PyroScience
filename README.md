# Outil de combinaison des données SBE19 et PyroScience AquaPhox-L

Cet outil sert à assigner les données d'oxygène de la sonde AquaPhox-L aux profils mesurés par la sonde SBE19. Il lit les fichiers CNV extraits par le logiciel SeaBird et les fichiers txt ou csv extraits par le logiciel PyroScience et les combine en un seul fichier.

Il nécessite que les données SeaBird et PyroScience soient sauvegardées sous un dossier commun.

### Instructions : 

1. Sur le côté, cliquez sur *Releases*, puis sur l'exécutable approprié pour votre OS afin de le télécharger.

   Attendez quelques instants (jusqu'à une minute).

3. Une fois téléchargé, extraire le .zip (sauf sous Windows) et double-cliquez sur l'icone de l'exécutable

   - **Linux** : Aucune instruction supplémentaire. Si rien ne se passe au moment de cliquer sur l'icone, exécutez le programme depuis un terminal (``./combiner_sbe19_aquaphox-linux``)

   - **Windows** : Windows va afficher "Windows a protégé votre ordinateur". Cliquez sur Informations complémentaires → Exécuter quand même

   - **MacOS** : MacOS bloquera le premier lancement de l’application. Allez dans Réglages Système → Confidentialité et sécurité → Ouvrir quand même.

4. Suivez les instructions.

   Les deux instruments sont équippés de sondes de température. On vous présentera des séries temporelles ces sondes, et on vous demandera de vérifier sur elles sont alignées. L'objectif est de les caller les unes sur les autres (horizontalement). Il est normal qu'il y ait une différence dans la température mesurée par les deux sondes (différence verticale).
