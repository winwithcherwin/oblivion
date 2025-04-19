import kopf
import datetime
import logging
import pygit2
import tempfile

from oblivion.control.ubuild import kaniko

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
)

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

    current_sha = get_latest_commit_sha(git_url, branch)


    if current_sha == last_commit:
        logger.info(f"🔁 No new commit on {branch}. Skipping build.")
        return

    logger.info(f"🚀 New commit detected: {current_sha[:7]} — triggering build.")
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
    job_result = kaniko.create_job(f"imagebuild-{current_sha[:5]}", git_url, image["name"])
    logger.info(f"would apply: {job_result}")

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

