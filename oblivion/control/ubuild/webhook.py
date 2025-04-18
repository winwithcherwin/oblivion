from kubernetes import client, config
from fastapi import FastAPI, Request
from datetime import datetime


app = FastAPI()

@app.post("/webhook/github")
async def receive_webhook(request: Request):
    headers = dict(request.headers)
    payload = await request.json()
    print(f"📥 Webhook received at {datetime.utcnow().isoformat()}Z")
    print("🔐 Headers:", headers)
    print("📦 Payload:", payload)

    repo_url = payload["repository"]["clone_url"]
    branch = payload["ref"].split("/")[-1]  # refs/heads/main → main
    commit = payload["after"]

    for crd in find_matching_imagebuilds(repo_url, branch):
        name = crd["metadata"]["name"]
        ns = crd["metadata"]["namespace"]
        print(f"Would have patched {ns}:{name}")

    return {"status": "ok"}

def find_matching_imagebuilds(repo_url, branch, namespace="default"):
    config.load_incluster_config()
    crd_api = client.CustomObjectsApi()

    all_ib = crd_api.list_namespaced_custom_object(
        group="ubuild.winwithcherwin.com",
        version="v1alpha1",
        namespace=namespace,
        plural="imagebuilds"
    )

    matches = []
    for item in all_ib["items"]:
        spec = item["spec"]
        if (
            spec["git"]["url"].rstrip(".git") == repo_url.rstrip(".git") and
            spec["git"].get("revision", "main") == branch
        ):
            matches.append(item)

    return matches
