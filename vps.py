import subprocess, time, uuid, threading

LOGS = {}          # user_id -> list of log lines
STATS = {}         # user_id -> {cpu, mem, uptime, started}
SUSPENDED = set()

def log(uid, msg):
    LOGS.setdefault(uid, []).append(f"[{time.strftime('%H:%M:%S')}] {msg}")

def run(cmd, capture=True):
    return subprocess.run(cmd, shell=True, capture_output=capture, text=True)

def create_vps(uid, username):
    name = f"vps_{username}_{uuid.uuid4().hex[:6]}"
    LOGS[uid] = []
    log(uid, "Allocating resources: 32GB RAM / 4 vCPU / 80GB disk...")
    time.sleep(1)
    log(uid, f"Pulling image ubuntu:22.04...")
    run("docker pull ubuntu:22.04")
    log(uid, "Image ready.")
    log(uid, f"Creating container {name}...")
    r = run(f"docker run -d --name {name} --memory=32g --cpus=4 "
            f"--storage-opt size=80G ubuntu:22.04 sleep infinity")
    if r.returncode != 0:
        # storage-opt fails on some drivers, retry without it
        run(f"docker rm -f {name}")
        r = run(f"docker run -d --name {name} --memory=32g --cpus=4 "
                f"ubuntu:22.04 sleep infinity")
        if r.returncode != 0:
            log(uid, f"ERROR: {r.stderr.strip()}")
            return None, None
    log(uid, "Container up. Installing tmate...")
    run(f"docker exec {name} bash -c 'apt-get update -qq && "
        f"DEBIAN_FRONTEND=noninteractive apt-get install -y -qq tmate openssh-client >/dev/null 2>&1'")
    log(uid, "Starting tmate session...")
    run(f"docker exec {name} bash -c 'rm -f /tmp/tmate.sock; "
        f"tmate -S /tmp/tmate.sock new-session -d && "
        f"tmate -S /tmp/tmate.sock wait tmate-ready'")
    ssh = run(f"docker exec {name} tmate -S /tmp/tmate.sock display -p '#{{tmate_ssh}}'").stdout.strip()
    log(uid, "SSH ready.")
    STATS[uid] = {"started": time.time(), "cpu": 0, "mem": 0, "uptime": 0}
    return name, ssh

def poll_stats(uid, container):
    r = run(f"docker stats {container} --no-stream --format '{{{{.CPUPerc}}}},{{{{.MemUsage}}}}'")
    if r.returncode != 0 or not r.stdout.strip():
        return
    try:
        cpu_s, mem_s = r.stdout.strip().split(',', 1)
        cpu = float(cpu_s.replace('%','').strip())
        mem = mem_s.split('/')[0].strip()
        STATS[uid]["cpu"] = cpu
        STATS[uid]["mem"] = mem
        STATS[uid]["uptime"] = int(time.time() - STATS[uid]["started"])
        if cpu > 80 and uid not in SUSPENDED:
            run(f"docker pause {container}")
            SUSPENDED.add(uid)
    except: pass

def suspend(container, uid):
    run(f"docker pause {container}")
    SUSPENDED.add(uid)

def unsuspend(container, uid):
    run(f"docker unpause {container}")
    SUSPENDED.discard(uid)

def destroy(container):
    run(f"docker rm -f {container}")

def monitor_loop(get_all_vps):
    while True:
        try:
            for row in get_all_vps():
                if row["status"] == "running":
                    poll_stats(row["user_id"], row["container_id"])
        except Exception as e:
            print("monitor err", e)
        time.sleep(8)

def start_monitor(get_all_vps):
    t = threading.Thread(target=monitor_loop, args=(get_all_vps,), daemon=True)
    t.start()
