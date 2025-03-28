import os

PLAYBOOK_ROOT = os.path.abspath("oblivion/engine/ansible/playbooks")

def list_available_playbooks():
    playbooks = []
    for dirpath, dirnames, files in os.walk(PLAYBOOK_ROOT):
        rel_path = os.path.relpath(dirpath, PLAYBOOK_ROOT)
        depth = rel_path.count(os.sep)

        if depth >= 2:
            dirnames[:] = []
            continue

        for f in files:
            if f.endswith((".yaml", ".yml")):
                full_path = os.path.join(dirpath, f)
                rel_path = os.path.relpath(full_path, PLAYBOOK_ROOT)
                clean_path = os.path.splitext(rel_path)[0]  # strip .yaml
                if clean_path.endswith("site"):
                    clean_path = clean_path.split("/")[0]
                playbooks.append(clean_path)
    return sorted(playbooks)

