# Лабораторна робота №5

## Резервне копіювання PostgreSQL у Kubernetes

### Опис

Реалізовано власний Kubernetes-ресурс DatabaseBackup та
Python-контролер, який автоматично створює і підтримує
CronJob для резервного копіювання PostgreSQL.

Резервні копії створюються утилітою pg_dump у форматі
CUSTOM і зберігаються на окремому PersistentVolumeClaim.

### Використані технології

- Kubernetes 1.37
- Kind
- Python 3.12
- Kubernetes Python Client
- PostgreSQL 17
- Docker
- CronJob
- CRD
- RBAC

### Встановлення

1. Створити кластер Kubernetes та namespace:

```bash
kind create cluster --config kind-lab5.yaml
kubectl create namespace demo
```

2. Розгорнути PostgreSQL:

```bash
kubectl apply -f lab5/postgres.yaml
kubectl wait --for=condition=Ready pod/postgres-0 \
  -n demo --timeout=180s
```

3. Зареєструвати CRD:

```bash
kubectl apply -f lab5/databasebackup-crd.yaml
```

4. Створити Secret, PVC та DatabaseBackup:

```bash
kubectl apply -f lab5/connection-secret.yaml
kubectl apply -f lab5/backup-pvc.yaml
kubectl apply -f lab5/databasebackup.yaml
```

5. Зібрати Docker-образ контролера:

```bash
docker build -t databasebackup-controller:1.2 \
  -f lab5/controller/Dockerfile lab5/controller

kind load docker-image databasebackup-controller:1.2 \
  --name lab5
```

6. Створити RBAC та Deployment:

```bash
kubectl apply -f lab5/controller-rbac.yaml
kubectl apply -f lab5/controller-deployment.yaml
```

### Перевірка роботи

Перегляд ресурсів:

```bash
kubectl get databasebackups,cronjobs -n demo
kubectl logs -n demo deployment/databasebackup-controller
```

Запуск ручного резервного копіювання:

```bash
kubectl create job backup-manual \
  --from=cronjob/users-db-backup-cronjob -n demo

kubectl wait --for=condition=complete \
  job/backup-manual -n demo --timeout=120s
```

Перегляд архівів через допоміжний Pod:

```bash
kubectl apply -f lab5/backup-inspector.yaml
kubectl exec -n demo backup-inspector -- ls -lh /backups
```

### Результати

- CRD DatabaseBackup зареєстровано.
- Python-контролер створює та оновлює CronJob.
- Видалений CronJob автоматично відновлюється.
- Права контролера обмежені namespace demo.
- Резервні копії зберігаються у PVC.
- Відновлення PostgreSQL через pg_restore перевірено.
- Контрольний запис успішно відновлено.
