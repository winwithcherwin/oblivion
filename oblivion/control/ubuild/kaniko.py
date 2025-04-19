import json

from kubernetes import client as k8s
from kubernetes.client import ApiClient
from kubernetes import config

def create_job(name, git_url, image_dest, revision="main", tag="latest", dockerfile="Dockerfile", dry_run=True):
    context_uri = f"git://{git_url}#refs/heads/{revision}"
    image_uri = f"{image_dest}:{tag}"

    job = k8s.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=k8s.V1ObjectMeta(name=name),
        spec=k8s.V1JobSpec(
            backoff_limit=0,
            template=k8s.V1PodTemplateSpec(
                spec=k8s.V1PodSpec(
                    restart_policy="Never",
                    containers=[
                        k8s.V1Container(
                            name="kaniko",
                            image="gcr.io/kaniko-project/executor:latest",
                            args=[
                                f"--context={context_uri}",
                                f"--dockerfile={dockerfile}",
                                f"--destination={image_uri}",
                                "--verbosity=debug",
                                f"--cache-repo={image_dest}",
                                "--cache=true",
                                "--cache-dir=/build/cache",
                            ],
                            volume_mounts=[
                                k8s.V1VolumeMount(name="kaniko-cache", mount_path="/build"),
                                k8s.V1VolumeMount(
                                    name="docker-config",
                                    mount_path="/kaniko/.docker/config.json",
                                    sub_path="config.json"
                                )
                            ]
                        )
                    ],
                    volumes=[
                        k8s.V1Volume(
                            name="kaniko-cache",
                            persistent_volume_claim=k8s.V1PersistentVolumeClaimVolumeSource(
                                claim_name="kaniko-cache-pvc"
                            )
                        ),
                        k8s.V1Volume(
                            name="docker-config",
                            secret=k8s.V1SecretVolumeSource(
                                secret_name="docker-pull-secret",
                                items=[
                                    k8s.V1KeyToPath(
                                        key=".dockerconfigjson",
                                        path="config.json"
                                    )
                                ]
                            )
                        )
                    ]
                )
            )
        )
    )

    if dry_run:
        job_dict = ApiClient().sanitize_for_serialization(job)
        print(json.dumps(job_dict, indent=2))
        return

    batch = k8s.BatchV1Api()
    batch.create_namespaced_job(namespace=namespace, body=job)


if __name__ == '__main__':
    config.load_kube_config()
    create_job("test-job", "github.com/winwithcherwin/oblivion.git", "registry.registry.svc.cluster.local:5000/oblivion")

