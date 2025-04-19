from kubernetes import client, config
from fastapi import FastAPI, Request
from datetime import datetime


app = FastAPI()

@app.post("/")
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

        trigger_paths = crd["spec"]["git"].get("triggerPaths", [])
        if not was_path_triggered(payload, trigger_paths):
            # return early
            return print("Nothing to do here, no path triggered")

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

def was_path_triggered(payload, trigger_paths):
    if not trigger_paths:
        # Trigger path not defined so assume always triggered
        return True

    all_paths = []
    for commit in payload.get("commits", []):
        all_paths  += commit.get("added", [])
        all_paths  += commit.get("modified", [])
        all_paths  += commit.get("removed", [])

    return any(any(path.startswith(trigger) for trigger in trigger_paths) for path in all_paths)
