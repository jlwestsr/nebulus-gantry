#!/bin/bash
set -e

echo "Starting Nebulus Gantry Bootstrap..."

# Check logic for Python 3.12+ could go here, but relying on system python for bootstrap is standard.

# Check for Ansible
if ! command -v ansible-playbook &> /dev/null; then
    echo "Ansible not found. Installing via pip (user)..."
    pip3 install --user ansible
fi

echo "Running Ansible Playbook..."
ansible-playbook -i ansible/inventory ansible/playbook.yml

echo "Bootstrap Complete! Run 'bin/run_app' to start."
