# **rapport_tp6.md — TP6 CI/CD pour systèmes ML + réentraînement automatisé + promotion MLflow**
NIAURONIS Tatiana – FIPA 3A  
CSC8613 – TP6

---

## **Exercice 1 — Mise en place du rapport et vérifications de départ**

### **Question 1.d**

Tous les services sont bien up :

```
(base) tatiananiauronis@MBP-de-tatiana TP1 % docker compose up -d 
[+] Running 7/7
 ✔ Container tp1-mlflow-1           Running                                        0.0s 
 ✔ Container tp1-postgres-1         Running                                        0.0s 
 ✔ Container tp1-feast-1            Running                                        0.0s 
 ✔ Container tp1-prefect-1          Running                                        0.0s 
 ✔ Container tp1-api-1              Running                                        0.0s 
 ✔ Container streamflow-prometheus  Running                                        0.0s 
 ✔ Container streamflow-grafana     Running                                        0.0s 
```

```
(base) tatiananiauronis@MBP-de-tatiana TP1 % docker compose ps
NAME                    IMAGE                           COMMAND                  SERVICE      CREATED       STATUS          PORTS
streamflow-grafana      grafana/grafana:11.2.0          "/run.sh"                grafana      2 weeks ago   Up 10 minutes   0.0.0.0:3000->3000/tcp, [::]:3000->3000/tcp
streamflow-prometheus   prom/prometheus:v2.55.1         "/bin/prometheus --c…"   prometheus   2 weeks ago   Up 10 minutes   0.0.0.0:9090->9090/tcp, [::]:9090->9090/tcp
tp1-api-1               tp1-api                         "uvicorn app:app --h…"   api          2 weeks ago   Up 10 minutes   0.0.0.0:8000->8000/tcp, [::]:8000->8000/tcp
tp1-feast-1             tp1-feast                       "bash -lc 'tail -f /…"   feast        3 weeks ago   Up 10 minutes   
tp1-mlflow-1            ghcr.io/mlflow/mlflow:v2.16.0   "mlflow server --bac…"   mlflow       2 weeks ago   Up 10 minutes   0.0.0.0:5001->5000/tcp, [::]:5001->5000/tcp
tp1-postgres-1          postgres:16                     "docker-entrypoint.s…"   postgres     2 weeks ago   Up 10 minutes   0.0.0.0:5432->5432/tcp, [::]:5432->5432/tcp
tp1-prefect-1           tp1-prefect                     "/usr/bin/tini -g --…"   prefect      2 weeks ago   Up 10 minutes 
```

C'est la version 3 qui est en production:

![alt text](image.png)

---

## **Exercice 2 — Ajouter une logique de décision testable (unit test)**

### **Question 2.d**

On a bien un succès pour la commande:

```
(base) tatiananiauronis@MBP-de-tatiana TP1 % pytest -q
..                                                                               [100%]
2 passed in 0.02s
```

On extrait une fonction pure pour pouvoir la tester rapidement et de façon déterministe, sans infrastructure ni effets de bord.

---

## **Exercice 3 — Créer le flow Prefect train_and_compare_flow (train → eval → compare → promote)**

### **Question 3.d**

Les logs du flow regroupent:

```
08:41:13.294 | INFO    | Task run 'evaluate_production-2f7' - Finished in state Completed()
[COMPARE] candidate_auc=0.6499 vs prod_auc=0.9391 (delta=0.0100)
[DECISION] skipped
08:41:13.339 | INFO    | Task run 'compare_and_promote-243' - Finished in state Completed()
[SUMMARY] as_of=2024-02-29 cand_v=4 cand_auc=0.6499 prod_v=3 prod_auc=0.9391 -> skipped
08:41:13.370 | INFO    | Flow run 'rare-boobook' - Finished in state Completed()
```

Dans MLFlow, on a bien une nouvelle version 4 mais la version 3 reste en Production car l'auc est de 0.6499 ce qui est inférieur à 0.9391+ delta:

![alt text](image-1.png)

Ici, on utilise un delta pour éviter de promouvoir un modèle pour une amélioration trop faible et trop proche de l'auc actuelle, on veut un gain significatif sur l'auc.

---

## **Exercice 4 — Connecter drift → retraining automatique (monitor_flow.py)**

### **Question 4.c**

Le drift s'est déclenché comme on peut le voir ici d'après les logs:

```
09:03:52.823 | INFO    | Task run 'decide_action-130' - Finished in state Completed()
[Evidently] report_html=/reports/evidently/drift_2024-01-31_vs_2024-02-29.html report_json=/reports/evidently/drift_2024-01-31_vs_2024-02-29.json drift_share=0.06 -> RETRAINING_TRIGGERED drift_share=0.06 >= 0.02 -> skipped
```
Un drift est détecté sur 6.25 % des features, principalement sur la variable rebuffer_events_7d comme on peut le voir ici :

![alt text](image-2.png)

---

## **Exercice 5 — Redémarrage API pour charger le nouveau modèle Production + test /predict**

### **Question 5.a**

On a redémarrer le service API:

```
(base) tatiananiauronis@MBP-de-tatiana TP1 % docker compose restart api 
[+] Restarting 1/1
 ✔ Container tp1-api-1  Started 
```

```
 api-1  | INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
api-1  | INFO:     172.19.0.7:44996 - "GET /metrics HTTP/1.1" 200 OK
```

































