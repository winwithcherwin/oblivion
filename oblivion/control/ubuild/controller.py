import base64
import kopf
import datetime
import logging
import pygit2
import tempfile
import secrets
import re

from urllib.parse import urlparse
from kubernetes import client

from github import Github
from github import Auth

from oblivion.control.ubuild import kaniko

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
)


@kopf.on.create('ubuild.winwithcherwin.com', 'v1alpha1', 'imagebuilds')
def create_webhook(spec, meta, status, namespace, name, logger, patch, **kwargs): 
    webhook_spec = spec["webhook"]
    if not webhook_spec["enabled"]:
        logger.info(f"{namespace}.{name}: webhook configured but not enabled")
        return

    secret = status.get("webhookSecret")
    if not secret:
        secret = secrets.token_hex(32)
        patch.status["webhookSecret"] = secret
        logger.info(f"{namespace}.{name}: Generated webhook secret")

    git_spec = spec["git"]

    webhook_type = webhook_spec["type"]

    if webhook_type == "github":
        # Only Github supported currently
        secret_ref = webhook_spec["secretRef"]
        secret_name = secret_ref["name"]
        secret_key = secret_ref["key"]
        token = get_secret_key(secret_name, secret_key, namespace)

        auth = Auth.Token(token)
        g = Github(auth=auth)

        url = resolve_webhook_url(spec, namespace)
        config = {
          "url": url,
          "content_type": "json",
          "secret": secret,
        }

        events = ["push"]

        owner, project = parse_github_url(git_spec["url"])
        repo = g.get_repo(f"{owner}/{project}")
        repo.create_hook("oblivion.ubuild", config, events, active=True)

        g.close()
        return

    logger.info(f"{namespace}.{name}: webhook type {webhook_type} not supported")

@kopf.timer('ubuild.winwithcherwin.com', 'v1alpha1', 'imagebuilds', interval=30)
@kopf.on.create('ubuild.winwithcherwin.com', 'v1alpha1', 'imagebuilds')
@kopf.on.update('ubuild.winwithcherwin.com', 'v1alpha1', 'imagebuilds')
def handle_build(spec, meta, status, namespace, name, logger, patch, **kwargs):
    def info(message):
        logger.info(f"{namespace}.{name}: {f'{message}'}")

    git = spec["git"]
    image = spec["image"]
    git_url = spec['git']['url']
    branch = spec['git'].get('revision', 'main')
    last_commit = status.get('lastCommit')

    # TODO: Make generic
    https_git_url = f"https://{git_url}" # is necessary for the git fetch
    current_sha = get_latest_commit_sha(https_git_url, branch)

    if current_sha == last_commit:
        info(f"🔁 No new commit on {branch}. Skipping build.")
        return

    info(f"🚀 New commit detected: {current_sha[:7]} — triggering build.")
    info(f"⏳ Starting DockerBuild for {git['url']} @ {git['revision']}")

    patch.status["buildPhase"] = "Building"
    patch.status["lastCommit"] = current_sha
    patch.status["lastBuildTime"] = datetime.datetime.utcnow().isoformat() + "Z"

    # Placeholder logic — no real build yet
    # Normally you'd trigger a Kaniko Job here
    info(f"📦 Would build {image['name']}:{git['revision'][:7]}")
    info(f"📂 Context dir: {git.get('contextDir', '.')}")
    info(f"📄 Dockerfile: {git.get('dockerfile', 'Dockerfile')}")

    # Output job result for inspection
    now = datetime.datetime.now().timestamp()
    tag = f"{branch}-{current_sha}-{now}"
    job_result = kaniko.create_job(f"imagebuild-{branch}-{current_sha[:5]}", git_url, image["name"], tag=tag, dry_run=False)
    info(f"would apply: {job_result}")

    # Simulate a successful build
    patch.status["buildPhase"] = "Succeeded"
    patch.status["lastImage"] = f"{image['name']}:{git['revision'][:7]}"
    patch.status["recentLogs"] = [
        f"Started build for {git['url']} at {git['revision']}",
        f"Image tag: {image['name']}:{git['revision'][:7]}"
    ]

    info(f"✅ Build succeeded.")

def get_latest_commit_sha(repo_url: str, branch: str = "main", username=None, token=None):
    if username and token:
        credentials = pygit2.UserPass(username, token)
    else:
        credentials = None

    callbacks = pygit2.RemoteCallbacks(credentials=credentials)

    with tempfile.TemporaryDirectory(prefix="bare-check-") as tmpdir:
        repo = pygit2.init_repository(tmpdir, bare=True)
        remote = repo.remotes.create("origin", repo_url)
        remote.fetch(callbacks=callbacks)

        refname = f"refs/remotes/origin/{branch}"
        if refname not in repo.references:
            raise ValueError(f"Branch '{branch}' not found in {repo_url}")

        sha = repo.references[refname].target
        return str(sha)

def resolve_webhook_url(spec, namespace):
    webhook = spec.get("webhook", {})
    if not webhook.get("enabled"):
        return None

    ingress_name = webhook["ingressRef"]

    networking = NetworkingV1Api()
    ingress = networking.read_namespaced_ingress(ingress_name, namespace)

    host = ingress.spec.rules[0].host
    path = ingress.spec.rules[0].paths[0].path
    return f"https://{host}{path}"

def get_secret_key(secret_name, key, namespace):
    v1 = client.CoreV1Api()
    secret = v1.read_namespaced_secret(secret_name, namespace)
    
    if key not in secret.data:
        raise ValueError(f"Key '{key}' not found in secret '{secret_name}'")
    
    # Secrets are base64-encoded, so decode them
    return base64.b64decode(secret.data[key]).decode("utf-8")

def parse_github_url(url):
    """Extract owner and repo from a GitHub URL (https, ssh, or raw)."""
    url = url.strip()

    # Case 1: git@github.com:owner/repo.git
    ssh_match = re.match(r"git@github\.com:(?P<owner>[^/]+)/(?P<repo>[^/]+?)(\.git)?$", url)
    if ssh_match:
        return ssh_match.group("owner"), ssh_match.group("repo")

    # Case 2: git://github.com/owner/repo.git or https://github.com/...
    if "://" not in url:
        url = "https://" + url  # Add scheme if missing for urlparse

    parsed = urlparse(url)
    if "github.com" not in parsed.netloc:
        raise ValueError("Only GitHub URLs are supported")

    parts = parsed.path.strip("/").split("/")
    if len(parts) < 2:
        raise ValueError("URL must be in the form github.com/owner/repo")

    owner = parts[0]
    repo = parts[1]
    if repo.endswith(".git"):
        repo = repo[:-4]

    return owner, repo

