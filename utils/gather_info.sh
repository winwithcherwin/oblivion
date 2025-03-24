ANSIBLE_SYSTEM_DIR=oblivion/engine/ansible/playbooks/system

echo "### MOTD FILE ###"
cat $ANSIBLE_SYSTEM_DIR/files/motd/_template
echo "### END MOTD FILE ###"

echo "### MOTD PLAYBOOK ###"
cat $ANSIBLE_SYSTEM_DIR/motd.yaml
echo "### END PLAYBOOK ###"
