from kubernetes import client, config
from fastapi import FastAPI, Request
from datetime import datetime


app = FastAPI()

def get_current_namespace():
    with open("/var/run/secrets/kubernetes.io/serviceaccount/namespace", "r") as f:
        return f.read().strip()

@app.get("/status")
async def status(request: Request):
    return {"status": "ok"}

@app.post("/")
async def receive_webhook(request: Request):
    headers = dict(request.headers)
    payload = await request.json()
    utc_now = datetime.utcnow().isoformat() + "Z"

    print(f"📥 Webhook received at {utc_now}")
    print("🔐 Headers:", headers)
    print("📦 Payload:", payload)

    if payload.get("zen", None):
        return {"status": "ok"}

    repo_url = payload["repository"]["clone_url"]
    branch = payload["ref"].split("/")[-1]  # refs/heads/main → main
    commit = payload["after"]

    namespace = get_current_namespace()

    print(f"Looking for image builds in: {namespace}")
    for crd in find_matching_imagebuilds(repo_url, branch, namespace):
        name = crd["metadata"]["name"]
        ns = crd["metadata"]["namespace"]

        trigger_paths = crd["spec"]["git"].get("triggerPaths", [])
        if not was_path_triggered(payload, trigger_paths):
            # return early
            return print("Nothing to do here, no path triggered")

        annotations = {
            "trigger-build": utc_now,
            "ubuild-commit-sha": commit,
        }
        print(f"[DEBUG] Annotating: {ns}:{name} with {annotations}")
        _ = annotate_imagebuild(name, ns, annotations)

    print("Processed trigger successfully.")
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
    print(f"All ubuilds: {all_ib}")

    matches = []
    for item in all_ib["items"]:
        spec = item["spec"]
        ib_git_url = spec["git"]["url"].rstrip(".git")
        repo_url = repo_url.rstrip(".git")
        repo_url = repo_url.removeprefix("https://") # quick and dirty to see if it works
        revision = spec["git"].get("revision", "main")
        print(f"[DEBUG] ubuild: '{ib_git_url}', webhook_repo: '{repo_url}', on branch {revision}")
        if (
            ib_git_url == repo_url and
            revision == branch
        ):
            matches.append(item)
    print(f"found matches: {len(matches)}")
    return matches

def was_path_triggered(payload, trigger_paths):
    print(f"Checking if we have triggered a path {trigger_paths}")
    if not trigger_paths:
        # Trigger path not defined so assume always triggered
        return True

    all_paths = []
    for commit in payload.get("commits", []):
        all_paths  += commit.get("added", [])
        all_paths  += commit.get("modified", [])
        all_paths  += commit.get("removed", [])

    print(f"All paths: {all_paths}")

    return any(any(path.startswith(trigger) for trigger in trigger_paths) for path in all_paths)

def annotate_imagebuild(name, namespace, annotations):
    config.load_incluster_config()  # or load_kube_config() for local dev
    api = client.CustomObjectsApi()

    patch = {
        "metadata": {
            "annotations": annotations,
        }
    }

    return api.patch_namespaced_custom_object(
        group="ubuild.winwithcherwin.com",
        version="v1alpha1",
        namespace=namespace,
        plural="imagebuilds",
        name=name,
        body=patch
    )
