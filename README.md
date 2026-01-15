# Local-Data-Lakehouse-Project

C'est une excellente approche pour l'apprentissage : comprendre la structure et les objectifs avant de s'attaquer à la syntaxe. Voici l'énoncé détaillé de votre POC pour le **"Local Data Lakehouse"**.

---

## Projet : Pipeline E-Commerce "Medallion Architecture"

### 1. L'Objectif

Concevoir un pipeline de données robuste qui transforme des données de ventes brutes (format JSON) en indicateurs de performance (KPI) exploitables, tout en respectant les standards de l'industrie pour la gestion d'un Data Lakehouse, le tout sur votre machine.

---

### 2. L'Infrastructure à monter (Docker)

Avant de toucher à Airflow, vous devez orchestrer trois services distincts :

1. **Orchestrateur :** Apache Airflow (gestion des workflows).
2. **Stockage Objet (S3 Local) :** **MinIO**. C'est ici que vos "buckets" (Bronze, Silver, Gold) résideront.
3. **Moteur de calcul :** **DuckDB** (intégré via Python) pour transformer et requêter les fichiers Parquet très rapidement.

---

### 3. Les Étapes du Pipeline (Le Workflow)

#### Étape A : Zone Bronze (Ingestion Brute)

* **Action :** Récupérer des fichiers JSON simulant des transactions e-commerce (ID, montant, date, client, produit).
* **Règle d'or :** On ne touche pas à la donnée. On la déplace simplement de la "source" vers le bucket `bronze` de MinIO.
* **Défi technique :** Gérer les connexions S3 dans Airflow et s'assurer que si on relance le pipeline, on ne crée pas de doublons désordonnés.

#### Étape B : Zone Silver (Nettoyage & Formatage)

* **Action :** Lire les fichiers JSON depuis la zone Bronze.
* **Transformations requises :**
* Caster les types (ex: s'assurer que le prix est un *float* et la date un objet *datetime*).
* Supprimer les lignes où l'ID transaction est manquant.
* Convertir le format : Passer du **JSON** au **Parquet** (format colonne optimisé pour le Big Data).


* **Destination :** Bucket `silver` sur MinIO.

#### Étape C : Zone Gold (Agrégation Business)

* **Action :** Utiliser DuckDB pour effectuer des jointures ou des agrégations SQL sur les fichiers Parquet de la zone Silver.
* **Objectif :** Créer une table finale (ou un fichier) "Daily Revenue" qui calcule le chiffre d'affaires total par catégorie de produit et par jour.
* **Destination :** Bucket `gold` sur MinIO ou base de données analytique locale.

---

### 4. Les Critères de Réussite (Le niveau "Avancé")

Pour que ce POC dépasse le niveau débutant, vous devez implémenter les concepts suivants :

1. **Idempotence & Partitionnement :** Vos fichiers dans MinIO ne doivent pas s'appeler `data.parquet`. Ils doivent suivre une structure de dossier temporelle : `/year=2024/month=01/day=15/data.parquet`. Cela permet de rejouer une journée spécifique sans impacter le reste.
2. **Gestion des Secrets :** Aucune clé d'accès MinIO ne doit être écrite en dur dans le code Python. Tout doit passer par les **Airflow Connections**.
3. **Data Quality (Simple) :** Ajouter une étape de vérification : si après la transformation Silver, le nombre de lignes est égal à zéro, le pipeline doit s'arrêter en erreur (Fail-fast).
4. **Nettoyage (Clean-up) :** Une tâche finale qui s'assure que les fichiers temporaires locaux (hors MinIO) sont bien supprimés.

---

### 5. Résumé de l'exercice pour vous

* **Entrée :** Un dossier local contenant des fichiers JSON "sales".
* **Sortie :** Un tableau de bord ou un fichier final dans le bucket Gold montrant l'évolution du CA.
* **Contrainte :** Tout doit passer par des opérateurs Airflow (`PythonOperator`, `BashOperator`, ou des opérateurs S3).

**Souhaitez-vous que je vous détaille d'abord la configuration du Docker-Compose pour lier Airflow et MinIO, ou préférez-vous réfléchir seul à la structure des tâches du DAG ?**