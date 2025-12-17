# **rapport_tp3.md — TP3 Introduction à Feast et au Feature Store pour StreamFlow**
NIAURONIS Tatiana – FIPA 3A  
CSC8613 – TP3

---

## **Exercice 1 — Setup initial, création du rapport et balisage Git**

### **Question 1.a**

![alt text](image.png)

Le tag pour le TP2 a bien été créé.

### **Question 1.b**

![alt text](image-1.png)

On a bien créé le repport dédié au TP 3.

# Contexte

Dans les TP précédents, nous avons mis en place un pipeline d’ingestion mensuelle pour la plateforme StreamFlow, avec stockage des données dans PostgreSQL et création de tables de snapshots (par exemple `subscriptions_profile_snapshots`, `usage_agg_30d_snapshots`, `payments_agg_90d_snapshots`, `support_agg_90d_snapshots`) pour le mois month_000 et month_001. Nous disposons donc déjà de données structurées sur les utilisateurs (profil, abonnements, usage de la plateforme, paiements, interactions avec le support) et d’un label de churn.  

L’objectif de ce TP3 est de brancher ces données existantes sur un Feature Store Feast pour préparer l’entraînement futur d’un modèle de churn et commencer à exposer les features en production. On va donc récupérer des features en mode offline et online pour construire un dataset d’entraînement et enfin exposer un endpoint d’API simple qui interroge Feast pour récupérer les features d’un utilisateur. Ce TP s’inscrit dans la suite logique du projet StreamFlow : préparer un système de ML prêt pour l’entraînement et la mise en production.


# Mise en place de Feast

Pour démarrer les services, on utilise la commande ```docker compose up -d --build```.

Le conteneur feast sert à exécuter le Feature Store Feast, qui centralise toute la logique de définition des entités, des FeatureViews, et des DataSources pointant vers PostgreSQL.

La configuration complète du Feature Store se trouve dans le dossier monté dans le conteneur  ```/repo``` dans lequel Feast lit feature_store.yaml, entities.py, data_sources.py et feature_views.py.

Pour utiliser Feast on fait:

```docker compose exec feast feast apply``` qui applique la configuration du Feature Store et génère registry.db et ```docker compose exec feast feast materialize ...```  qui remplit le online store pour l’inférence en temps réel.

# Définition du Feature Store

Dans Feast, une Entity représente l'objet au sens métier auquel les features sont rattachées. Elle sert d'identifiant unique permettant d'associer correctement les données issues de différentes sources. Dans le projet StreamFlow, l'entité centrale est l’utilisateur, car toutes les features (usage, abonnements, paiements, support…) décrivent le comportement d’un même client.
Le champ user_id est un excellent choix de clé de jointure, car il apparaît dans toutes les tables de snapshots et permet de relier l’ensemble des features de manière cohérente.

Pour chaque `PostgreSQLSource`, la requête SQL ne sélectionne que les colonnes nécessaires : `user_id`, `as_of` et les colonnes de features pertinentes. On évite ainsi de charger des colonnes inutiles.

Par exemple, pour la table de snapshot `usage_agg_30d_snapshots`, nous utilisons les features suivantes :
- `watch_hours_30d` qui est le nombre d’heures regardées sur les 30 derniers jours
- `avg_session_mins_7d` la durée moyenne de session sur 7 jours
- `unique_devices_30d` le nombre de devices distincts utilisés
- `skips_7d` le nombre de skips sur 7 jours.

Le champ `timestamp_field = "as_of"` est essentiel car cela permet à Feast de faire les jointures temporelles correctes (point-in-time correctness) lorsqu’on récupère les features pour une date donnée.

# Récupération offline & online

Le fichier data/processed/training_df.csv a bien été créé. La commande utilisée est ```docker compose exec prefect python build_training_dataset.py```.

Les 5 première lignes du fichier sont:

```
(base) tatiananiauronis@MBP-de-tatiana TP1 % head -5 data/processed/training_df.csv
user_id,event_timestamp,months_active,monthly_fee,paperless_billing,watch_hours_30d,avg_session_mins_7d,failed_payments_90d,churn_label
7639-LIAYI,2024-01-31,52,79.75,True,28.7551480294639,29.141044640845102,1,False
9919-YLNNG,2024-01-31,42,103.8,True,34.9661477745677,29.141044640845102,0,False
0318-ZOPWS,2024-01-31,49,20.150000000000002,True,22.0360788601714,29.141044640845102,0,False
4445-ZJNMU,2024-01-31,9,99.3,True,29.3246642842447,29.141044640845102,1,False
```
Feast garantit la point-in-time correctness parce que chaque DataSource est déclarée avec timestamp_field="as_of" . Cela indique à Feast quelle colonne représente la date de validité des features dans les snapshots. Ensuite, dans entity_df, on fournit pour chaque user_id un event_timestamp (ici égal à as_of), donc Feast va récupérer uniquement les valeurs de features correspondant à cette date (et pas des valeurs du futur). 

On obtient après avoir complété la fonction debug_online_features.py:

```
{'user_id': ['7892-POOKP'], 'paperless_billing': [True], 'months_active': [28], 'monthly_fee': [104.80000305175781]}
```

Ces valeurs correspondent aux features matérialisées dans l’online store pour cet utilisateur à partir des snapshots mensuels.

Si l’on interroge un user_id qui n’existe pas dans les données ou qui est en dehors de la fenêtre de matérialisation, Feast ne trouve aucune feature associée dans l’Online Store. Les valeurs retournées sont alors ```None``` ou NaN, car aucune donnée n’a été écrite pour cet utilisateur à cette période: 

```
{'user_id': ['7892-POOKPs'], 'paperless_billing': [None], 'months_active': [None], 'monthly_fee': [None]}
```

Après avoir exécuté la commande ```curl http://localhost:8000/features/7892-POOKP```, j'obtiens:

```
{"user_id":"7892-POOKP","features":{"user_id":"7892-POOKP","paperless_billing":true,"months_active":28,"monthly_fee":104.80000305175781}}% 
```

# Réflexion

L’endpoint /features/{user_id} réduit le training-serving skew car il s’appuie exactement sur les mêmes FeatureViews Feast que celles utilisées pour construire le jeu de données d’entraînement. Les features ne sont pas recalculées manuellement dans l’API, mais récupérées depuis le Feature Store, avec la même logique et les mêmes sources de données. Cela garantit que le modèle voit les mêmes features en entraînement et en production. 


