import subprocess
import time
import requests
import statistics

print("\n🧠 RESEARCH AI AUTOSCALER STARTED\n")

# ================================
# CONFIG
# ================================

MODEL_API = "http://127.0.0.1:35863/predict"
NAMESPACE = "default"

CRITICAL_DEPLOY = "critical-app"
NONCRITICAL_DEPLOY = "noncritical-app"

# CLUSTER LIMIT
MAX_TOTAL_PODS = 8

# BASELINE (never go below)
CRITICAL_BASE = 2
NONCRITICAL_BASE = 1

# MAX LIMIT PER SERVICE
CRITICAL_MAX = 7
NON_CRITICAL_BASE = 3  # max noncritical can reach when critical is NOT stressed

# COOLDOWN
COOLDOWN = 15
last_scaled = 0

cpu_history = []

# imbalance config
IMBALANCE_RATIO = 3.0
IMBALANCE_MIN_CPU = 50

service_map = {"patient_monitoring": 5}
type_map = {"critical": 0, "noncritical": 1}

# ==========================================
# GET REPLICAS
# ==========================================
def get_replicas(deploy):
    try:
        r = subprocess.check_output([
            "kubectl", "get", "deployment", deploy,
            "-o", "jsonpath={.spec.replicas}"
        ]).decode().strip()
        return int(r)
    except:
        return 0

# ==========================================
# SCALE
# ==========================================
def scale(deploy, replicas):
    print(f"⚡ Scaling {deploy} → {replicas}")
    subprocess.run([
        "kubectl","scale","deployment",deploy,
        f"--replicas={replicas}"
    ])

# ==========================================
# GET CPU PER SERVICE
# ==========================================
def get_service_cpu(deploy):
    try:
        out = subprocess.check_output(
            ["kubectl","top","pods","-l",f"app={deploy}","-n",NAMESPACE],
            stderr=subprocess.DEVNULL
        ).decode()

        lines = out.strip().split("\n")[1:]

        cpus=[]
        mems=[]

        for l in lines:
            p=l.split()
            cpu=int(p[1].replace("m",""))
            mem=int(p[2].replace("Mi",""))
            cpus.append(cpu)
            mems.append(mem)

        if not cpus:
            return 0,0

        avg=sum(cpus)/len(cpus)
        mx=max(cpus)

        final=(0.8*mx)+(0.2*avg)

        cpu_percent=min(final,100)
        mem_percent=min((max(mems)/10),100)

        return cpu_percent, mem_percent

    except:
        return 0,0

# ==========================================
# REQUEST RATE
# ==========================================
def get_request_rate():
    try:
        pod = subprocess.check_output(
            ["kubectl","get","pods","-o","jsonpath={.items[0].metadata.name}"]
        ).decode().strip()

        logs = subprocess.check_output(
            ["kubectl","logs",pod,"--since=5s"],
            stderr=subprocess.DEVNULL
        ).decode()

        return logs.count("GET")+logs.count("POST")
    except:
        return 0

# ==========================================
# SPIKE DETECT
# ==========================================
def spike_detect(cpu):
    cpu_history.append(cpu)
    if len(cpu_history)>5:
        cpu_history.pop(0)

    if len(cpu_history)>=3:
        if cpu_history[-1]>(statistics.mean(cpu_history[:-1])*1.4):
            print("🚨 CPU SPIKE DETECTED")
            return True
    return False

# ==========================================
# PER POD CPU
# ==========================================
def get_per_pod_cpu(deploy):
    try:
        output = subprocess.check_output(
            ["kubectl","top","pods","-l",f"app={deploy}","-n",NAMESPACE],
            stderr=subprocess.DEVNULL
        ).decode()

        pods=[]
        for line in output.strip().split("\n")[1:]:
            parts=line.split()
            if len(parts)<3: continue
            name=parts[0]
            cpu=int(parts[1].replace("m",""))
            pods.append((name,cpu))
        return pods
    except:
        return []

# ==========================================
# LOAD IMBALANCE FIX
# ==========================================
def detect_and_fix_imbalance(deploy):
    pods=get_per_pod_cpu(deploy)
    if len(pods)<2:
        return

    cpus=[c for _,c in pods]
    avg=statistics.mean(cpus)
    hot_pod,hot_cpu=max(pods,key=lambda x:x[1])

    if hot_cpu>=IMBALANCE_MIN_CPU and avg>0 and (hot_cpu/avg)>=IMBALANCE_RATIO:

        print(f"\n🔀 LOAD IMBALANCE [{deploy}]")
        print(f"Hot pod: {hot_pod} = {hot_cpu}m")

        subprocess.run([
            "kubectl","label","pod",hot_pod,
            f"app={deploy}-draining","--overwrite","-n",NAMESPACE
        ],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

        time.sleep(5)

        subprocess.run([
            "kubectl","delete","pod",hot_pod,
            "-n",NAMESPACE,"--grace-period=10"
        ],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)

        print("✅ Hot pod restarted for balance")

# ==========================================
# MAIN LOOP
# ==========================================
while True:

    detect_and_fix_imbalance(CRITICAL_DEPLOY)
    detect_and_fix_imbalance(NONCRITICAL_DEPLOY)

    critical_cpu, critical_mem = get_service_cpu(CRITICAL_DEPLOY)
    noncritical_cpu, noncritical_mem = get_service_cpu(NONCRITICAL_DEPLOY)

    critical=get_replicas(CRITICAL_DEPLOY)
    noncritical=get_replicas(NONCRITICAL_DEPLOY)
    total=critical+noncritical

    req=get_request_rate()
    errors=0

    # =============================================
    # 📊 PHASE 1: CRITICAL PODS MEASUREMENT (FIRST)
    # =============================================

    crit_latency=50+(critical_cpu*0.5)
    crit_predicted_load=0.5*critical_cpu+0.3*critical_mem+0.2*(crit_latency/2)

    crit_features=[
        critical_cpu, critical_mem, crit_latency, errors,
        req, critical, crit_predicted_load,
        service_map["patient_monitoring"],
        type_map["critical"]
    ]

    print("\n" + "="*50)
    print("📊 CRITICAL FEATURES:", crit_features)

    try:
        crit_res=requests.post(MODEL_API,json={"features":crit_features},timeout=5)
        crit_data=crit_res.json()
        crit_action=crit_data.get("predicted_action","stable")
        print("🤖 CRITICAL MODEL:", crit_data)
    except Exception as e:
        print("Critical model error:",e)
        time.sleep(5)
        continue

    # -----------------------------------------
    # 🚨 CRITICAL STRESS CHECK + PREEMPTION
    # -----------------------------------------
    critical_stressed = critical_cpu > 60

    if time.time()-last_scaled >= COOLDOWN:

        if crit_action=="scale_up" or spike_detect(critical_cpu):

            print("\n⚡ CRITICAL AUTOSCALING ENGINE")

            if critical_stressed:

                print("🚨 CRITICAL UNDER HIGH STRESS")

                # AGGRESSIVE PREEMPTION: kill ALL noncritical down to 1
                # 7 out of 8 pods should be critical
                if noncritical > NONCRITICAL_BASE:
                    print(f"🔥 PREEMPTION: Killing ALL noncritical down to {NONCRITICAL_BASE} (freeing {noncritical - NONCRITICAL_BASE} slots)")
                    scale(NONCRITICAL_DEPLOY, NONCRITICAL_BASE)
                    freed = noncritical - NONCRITICAL_BASE
                    noncritical = NONCRITICAL_BASE
                    total = critical + noncritical
                    time.sleep(2)

                # Scale critical up to fill available slots (up to 7)
                desired_critical = min(MAX_TOTAL_PODS - NONCRITICAL_BASE, CRITICAL_MAX)
                if critical < desired_critical:
                    new_critical = min(desired_critical, MAX_TOTAL_PODS - noncritical)
                    if new_critical > critical:
                        print(f"⬆ Scaling CRITICAL {critical} → {new_critical}")
                        scale(CRITICAL_DEPLOY, new_critical)
                        critical = new_critical
                        total = critical + noncritical

            else:
                # critical not at extreme stress but model says scale up
                if total < MAX_TOTAL_PODS:
                    print("⬆ Scaling CRITICAL (cluster has space)")
                    scale(CRITICAL_DEPLOY, critical+1)
                    critical += 1
                    total += 1

                elif noncritical > NONCRITICAL_BASE:
                    print("🔥 PREEMPTION: Killing 1 NONCRITICAL for CRITICAL")
                    scale(NONCRITICAL_DEPLOY, noncritical-1)
                    time.sleep(2)
                    noncritical -= 1
                    scale(CRITICAL_DEPLOY, critical+1)
                    critical += 1
                    total = critical + noncritical

                else:
                    print("❌ Cannot scale critical further")

            last_scaled=time.time()

        elif crit_action=="scale_down":

            if critical > CRITICAL_BASE:
                print("⬇ AI scale down CRITICAL")
                scale(CRITICAL_DEPLOY, critical-1)
                critical -= 1
                total = critical + noncritical
                last_scaled=time.time()

        else:
            # stable — reduce excess critical if overprovisioned
            if critical_cpu < 25 and critical > CRITICAL_BASE:
                print("⬇ Reducing excess CRITICAL pods")
                scale(CRITICAL_DEPLOY, critical-1)
                critical -= 1
                total = critical + noncritical
                last_scaled=time.time()

    else:
        print("⏳ Cooldown active (critical phase)")

    # =============================================
    # � PHASE 2: NON-CRITICAL PODS MEASUREMENT (SECOND)
    # =============================================

    nc_latency=50+(noncritical_cpu*0.5)
    nc_predicted_load=0.5*noncritical_cpu+0.3*noncritical_mem+0.2*(nc_latency/2)

    nc_features=[
        noncritical_cpu, noncritical_mem, nc_latency, errors,
        req, noncritical, nc_predicted_load,
        service_map["patient_monitoring"],
        type_map["noncritical"]
    ]

    print("\n" + "="*50)
    print("📊 NONCRITICAL FEATURES:", nc_features)

    try:
        nc_res=requests.post(MODEL_API,json={"features":nc_features},timeout=5)
        nc_data=nc_res.json()
        nc_action=nc_data.get("predicted_action","stable")
        print("🤖 NONCRITICAL MODEL:", nc_data)
    except Exception as e:
        print("Noncritical model error:",e)
        time.sleep(5)
        continue

    # -----------------------------------------
    # 📦 NON-CRITICAL SCALING (GUARDED BY CRITICAL STRESS)
    # -----------------------------------------
    # re-check critical stress (may have changed after scaling)
    critical_stressed = critical_cpu > 60

    if time.time()-last_scaled >= COOLDOWN:

        if nc_action=="scale_up":

            if critical_stressed:
                print("🚫 NONCRITICAL scale-up BLOCKED — critical is under stress")

            else:
                # critical is NOT stressed → allow noncritical up to NON_CRITICAL_BASE
                if noncritical < NON_CRITICAL_BASE and total < MAX_TOTAL_PODS:
                    print(f"📦 Scaling NONCRITICAL (critical is safe, up to {NON_CRITICAL_BASE})")
                    scale(NONCRITICAL_DEPLOY, noncritical+1)
                    noncritical += 1
                    total = critical + noncritical
                else:
                    print("⚠ Noncritical at max allowed or cluster full")

            last_scaled=time.time()

        elif nc_action=="scale_down":

            if noncritical > NONCRITICAL_BASE:
                print("⬇ AI scale down NONCRITICAL")
                scale(NONCRITICAL_DEPLOY, noncritical-1)
                noncritical -= 1
                total = critical + noncritical
                last_scaled=time.time()

        else:
            # stable noncritical
            print("🧊 Noncritical stable")

            if not critical_stressed:
                # allow noncritical recovery if below baseline and critical safe
                if noncritical < NONCRITICAL_BASE:
                    print("🟢 Restoring NONCRITICAL to baseline")
                    scale(NONCRITICAL_DEPLOY, NONCRITICAL_BASE)
                    noncritical = NONCRITICAL_BASE
                    total = critical + noncritical
                    last_scaled=time.time()

                elif noncritical < NON_CRITICAL_BASE and total < MAX_TOTAL_PODS:
                    print("📈 Recovering NONCRITICAL gradually")
                    scale(NONCRITICAL_DEPLOY, noncritical+1)
                    noncritical += 1
                    total = critical + noncritical
                    last_scaled=time.time()

            # reduce excess noncritical if idle
            if noncritical_cpu < 20 and noncritical > NONCRITICAL_BASE:
                print("⬇ Reducing excess NONCRITICAL pods")
                scale(NONCRITICAL_DEPLOY, noncritical-1)
                noncritical -= 1
                total = critical + noncritical
                last_scaled=time.time()

    else:
        print("⏳ Cooldown active (noncritical phase)")

    # =============================================
    # CLUSTER STATUS
    # =============================================
    print(f"\n📋 CLUSTER: critical={critical} noncritical={noncritical} total={total}/{MAX_TOTAL_PODS}")
    print(f"   CPU: critical={critical_cpu:.1f}% noncritical={noncritical_cpu:.1f}%")

    if (
        critical_cpu < 40 and
        noncritical_cpu < 40 and
        critical == CRITICAL_BASE and
        noncritical == NONCRITICAL_BASE
    ):
        print("🟢 Cluster perfectly balanced")

    time.sleep(6)
