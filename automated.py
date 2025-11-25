#!/usr/bin/env python3
import argparse, csv, os, re, shlex, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from getpass import getpass
from pathlib import Path
from typing import List, Optional, Tuple

PLAYBOOK_REGEX = re.compile(r"^\d+\.ya?ml$", re.IGNORECASE)

@dataclass
class Task:
    folder: Path
    inventory: Path
    playbook: Path

def discover_tasks(root: Path, inventory_name: str) -> List[Task]:
    tasks = []
    for p in sorted(root.rglob(inventory_name)):
        folder = p.parent
        candidates = sorted([f for f in folder.glob("*.y*ml") if f.name != inventory_name])
        if not candidates: continue
        # เน้นชื่อเป็นตัวเลข such as 11242.yaml
        num = [f for f in candidates if PLAYBOOK_REGEX.match(f.name)]
        chosen = num[0] if num else candidates[0]
        tasks.append(Task(folder=folder, inventory=p, playbook=chosen))
    return tasks

def run_task(task: Task, user: str, ssh_pass: Optional[str], become_pass: Optional[str],
             check: bool, env: dict, log_dir: Path) -> Tuple[Task,int,float,str]:
    cmd = ["ansible-playbook","-i",str(task.inventory),str(task.playbook),"-u",user]
    if check: cmd.append("--check")
    ev_pairs = []
    if ssh_pass: ev_pairs.append(f"ansible_password={ssh_pass}")
    if become_pass: ev_pairs.append(f"ansible_become_pass={become_pass}")
    if ev_pairs: cmd += ["--extra-vars"," ".join(ev_pairs)]

    start=time.time()
    log_file=log_dir/f"{task.folder.name}__{task.playbook.name}.log"
    with log_file.open("w",encoding="utf-8",errors="ignore") as lf:
        # log คำสั่ง แต่ redact password
        _cmd_str=" ".join(shlex.quote(c) for c in cmd)
        _cmd_str=_cmd_str.replace("ansible_password=","ansible_password=***").replace("ansible_become_pass=","ansible_become_pass=***")
        lf.write(f"$ {_cmd_str}\n\n")
        try:
            proc=subprocess.run(cmd,stdout=lf,stderr=subprocess.STDOUT,env=env,cwd=task.folder)
            rc=proc.returncode
        except Exception as e:
            lf.write(f"ERROR: {e}\n")
            rc=1
    dur=time.time()-start
    status="PASS" if rc==0 else f"FAIL({rc})"
    return task,rc,dur,status

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=".")
    ap.add_argument("--inventory-name",default="inventory.ini")
    ap.add_argument("-u","--user",required=True)
    ap.add_argument("--ask-pass-once",action="store_true")
    ap.add_argument("--ask-become-pass-once",action="store_true")
    ap.add_argument("--check",action="store_true")
    args=ap.parse_args()

    root=Path(args.root).resolve()
    tasks=discover_tasks(root,args.inventory_name)
    if not tasks: sys.exit("No tasks found")

    ssh_pass=getpass("SSH password: ") if args.ask_pass_once else None
    become_pass=getpass("BECOME password: ") if args.ask_become_pass_once else None

    env=os.environ.copy()
    log_dir=root/"ansible-batch-logs"; log_dir.mkdir(exist_ok=True)
    summary=root/"ansible_batch_summary.csv"
    rows=[]

    for t in tasks:
        task,rc,dur,status=run_task(t,args.user,ssh_pass,become_pass,args.check,env,log_dir)
        print(f"[{status}] {t.folder.name}/{t.playbook.name} in {dur:.1f}s")
        rows.append([t.folder.name,t.inventory.name,t.playbook.name,status,f"{dur:.1f}"])

    with summary.open("w",newline="",encoding="utf-8") as f:
        writer=csv.writer(f); writer.writerow(["folder","inventory","playbook","status","duration_s"]); writer.writerows(rows)
    print(f"\nSummary: {summary}\nLogs: {log_dir}")

if __name__=="__main__":
    main()
