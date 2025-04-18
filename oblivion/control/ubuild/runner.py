import asyncio
import kopf
import kubernetes

from oblivion.control.ubuild import controller
from kubernetes.config import ConfigException


def load_kube_config():
    try:
        # Try in-cluster config (for production)
        kubernetes.config.load_incluster_config()
        print("🔐 Using in-cluster config")
    except ConfigException:
        # Fall back to local kubeconfig (for dev/testing)
        kubernetes.config.load_kube_config()
        print("🧪 Using local kubeconfig")

def run():
    load_kube_config()
    asyncio.run(kopf.operator(
      standalone=True,
      clusterwide=True,
    ))
