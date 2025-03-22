import os

PLAYBOOK_ROOT = os.path.abspath("oblivion/engine/ansible/playbooks")

def list_available_playbooks():
    playbooks = []
    for root, _, files in os.walk(PLAYBOOK_ROOT):
        for f in files:
            if f.endswith((".yaml", ".yml")):
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, PLAYBOOK_ROOT)
                clean_path = os.path.splitext(rel_path)[0]  # strip .yaml
                playbooks.append(clean_path)
    return sorted(playbooks)

