# Running Ansible Playbook

**Warning:** Running in real mode will affect the system.

## Real Run
$ ansible-playbook -i <inventory.ini> <playbook.yaml> -u <user for login> --ask-pass --ask-become-pass

When you run the command, enter the password when prompted.

---

## Check Mode (Dry Run)
$ ansible-playbook -i <inventory.ini> <playbook.yaml> -u <user for login> --ask-pass --ask-become-pass --check --diff

This will **simulate the run** and show the differences (diff) without making any actual changes to the system.

---

## Example inventory.ini
[Default]
hostname1 ansible_host=172.16.220.2x
hostname2 ansible_host=172.16.220.2x

---

If use python
$ python3 automated.py --root . -u root --ask-pass-once --ask-become-pass-once

---