import logging
import os
import time

from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

NAMESPACE = os.getenv("WATCH_NAMESPACE", "demo")
GROUP = "backup.example.com"
VERSION = "v1alpha1"
PLURAL = "databasebackups"
BACKUP_IMAGE = "postgres:17-alpine"


def load_configuration():
    try:
        config.load_incluster_config()
        logger.info("Loaded in-cluster configuration")
    except config.ConfigException:
        config.load_kube_config()
        logger.info("Loaded local kubeconfig")


def cronjob_name(resource):
    return f"{resource['metadata']['name']}-cronjob"


def build_cronjob(resource):
    metadata = resource["metadata"]
    spec = resource["spec"]

    backup_script = """
set -eu

TMP=$(mktemp /backups/.backup-XXXXXXXX)
FILE="/backups/${PGDATABASE}-$(date -u +%Y%m%dT%H%M%SZ)-${HOSTNAME}.dump"

trap 'rm -f "$TMP"' EXIT

pg_dump -Fc -f "$TMP"
test -s "$TMP"

mv "$TMP" "$FILE"

echo "Backup created: $FILE"
"""

    return {
        "apiVersion": "batch/v1",
        "kind": "CronJob",
        "metadata": {
            "name": cronjob_name(resource),
            "namespace": metadata["namespace"],
            "ownerReferences": [
                {
                    "apiVersion": f"{GROUP}/{VERSION}",
                    "kind": "DatabaseBackup",
                    "name": metadata["name"],
                    "uid": metadata["uid"],
                    "controller": True,
                    "blockOwnerDeletion": False,
                }
            ],
        },
        "spec": {
            "schedule": spec["schedule"],
            "timeZone": spec.get("timeZone", "Etc/UTC"),
            "concurrencyPolicy": "Forbid",
            "successfulJobsHistoryLimit": 2,
            "failedJobsHistoryLimit": 2,
            "jobTemplate": {
                "spec": {
                    "template": {
                        "spec": {
                            "restartPolicy": "Never",
                            "containers": [
                                {
                                    "name": "pg-dump",
                                    "image": BACKUP_IMAGE,
                                    "command": ["/bin/sh", "-ec"],
                                    "args": [backup_script],
                                    "envFrom": [
                                        {
                                            "secretRef": {
                                                "name": spec[
                                                    "connectionSecretName"
                                                ]
                                            }
                                        }
                                    ],
                                    "volumeMounts": [
                                        {
                                            "name": "backup-storage",
                                            "mountPath": "/backups",
                                        }
                                    ],
                                }
                            ],
                            "volumes": [
                                {
                                    "name": "backup-storage",
                                    "persistentVolumeClaim": {
                                        "claimName": spec["backupPVCName"]
                                    },
                                }
                            ],
                        }
                    }
                }
            },
        },
    }


def is_owned_by(cronjob, resource):
    owners = cronjob.metadata.owner_references or []

    return any(
        owner.uid == resource["metadata"]["uid"]
        and owner.kind == "DatabaseBackup"
        and owner.controller is True
        for owner in owners
    )


def current_config(cronjob):
    spec = cronjob.spec
    pod_spec = spec.job_template.spec.template.spec

    container = pod_spec.containers[0]

    secret_name = None
    for env in container.env_from or []:
        if env.secret_ref:
            secret_name = env.secret_ref.name
            break

    pvc_name = None
    for volume in pod_spec.volumes or []:
        if volume.name == "backup-storage":
            if volume.persistent_volume_claim:
                pvc_name = volume.persistent_volume_claim.claim_name
            break

    return {
        "schedule": spec.schedule,
        "timeZone": spec.time_zone,
        "concurrencyPolicy": spec.concurrency_policy,
        "image": container.image,
        "command": container.command,
        "args": container.args,
        "secret": secret_name,
        "pvc": pvc_name,
    }


def desired_config(desired):
    spec = desired["spec"]
    pod_spec = spec["jobTemplate"]["spec"]["template"]["spec"]
    container = pod_spec["containers"][0]

    return {
        "schedule": spec["schedule"],
        "timeZone": spec["timeZone"],
        "concurrencyPolicy": spec["concurrencyPolicy"],
        "image": container["image"],
        "command": container["command"],
        "args": container["args"],
        "secret": container["envFrom"][0]["secretRef"]["name"],
        "pvc": pod_spec["volumes"][0][
            "persistentVolumeClaim"
        ]["claimName"],
    }


def reconcile(resource, batch_api):
    namespace = resource["metadata"]["namespace"]
    name = cronjob_name(resource)

    desired = build_cronjob(resource)

    try:
        existing = batch_api.read_namespaced_cron_job(
            name=name,
            namespace=namespace,
        )

    except ApiException as error:
        if error.status != 404:
            raise

        try:
            batch_api.create_namespaced_cron_job(
                namespace=namespace,
                body=desired,
            )
            logger.info("Created CronJob %s", name)
        except ApiException as create_error:
            if create_error.status != 409:
                raise
            logger.info("CronJob %s was created concurrently", name)
        return

    if not is_owned_by(existing, resource):
        logger.error(
            "Conflict: CronJob %s is not owned by DatabaseBackup %s",
            name,
            resource["metadata"]["name"],
        )
        return

    if current_config(existing) == desired_config(desired):
        logger.info("CronJob %s is up to date", name)
        return

    batch_api.patch_namespaced_cron_job(
        name=name,
        namespace=namespace,
        body={"spec": desired["spec"]},
    )

    logger.info("Updated CronJob %s", name)


def reconcile_by_name(name, custom_api, batch_api):
    try:
        resource = custom_api.get_namespaced_custom_object(
            group=GROUP,
            version=VERSION,
            namespace=NAMESPACE,
            plural=PLURAL,
            name=name,
        )
    except ApiException as error:
        if error.status == 404:
            return
        raise

    reconcile(resource, batch_api)


def list_and_reconcile(custom_api, batch_api):
    result = custom_api.list_namespaced_custom_object(
        group=GROUP,
        version=VERSION,
        namespace=NAMESPACE,
        plural=PLURAL,
    )

    for resource in result.get("items", []):
        try:
            reconcile_by_name(
                resource["metadata"]["name"],
                custom_api,
                batch_api,
            )
        except Exception:
            logger.exception("Failed to reconcile resource")

    return result["metadata"]["resourceVersion"]


def main():
    load_configuration()

    custom_api = client.CustomObjectsApi()
    batch_api = client.BatchV1Api()

    logger.info("DatabaseBackup controller started")

    while True:
        try:
            resource_version = list_and_reconcile(
                custom_api,
                batch_api,
            )

            watcher = watch.Watch()

            for event in watcher.stream(
                custom_api.list_namespaced_custom_object,
                group=GROUP,
                version=VERSION,
                namespace=NAMESPACE,
                plural=PLURAL,
                resource_version=resource_version,
                timeout_seconds=30,
            ):
                if event["type"] not in ("ADDED", "MODIFIED"):
                    continue

                name = event["object"]["metadata"]["name"]

                reconcile_by_name(
                    name,
                    custom_api,
                    batch_api,
                )

        except ApiException as error:
            if error.status == 410:
                logger.warning(
                    "ResourceVersion expired; restarting LIST/WATCH"
                )
                continue

            logger.exception("Kubernetes API error")
            time.sleep(3)

        except Exception:
            logger.exception("Controller error")
            time.sleep(3)


if __name__ == "__main__":
    main()
