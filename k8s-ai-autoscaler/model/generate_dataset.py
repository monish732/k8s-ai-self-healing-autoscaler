import pandas as pd
import random

print("\n🧠 Generating AI Autoscaler Dataset...\n")

rows = []

services = [
    "patient_monitoring",
    "pharmacy",
    "lab_report",
    "analytics",
    "emergency"
]

for i in range(60000):   # dataset size

    # =============================
    # RANDOM BASE METRICS
    # =============================
    cpu = random.randint(1,100)
    memory = random.randint(5,95)
    latency = random.randint(20,400)
    errors = random.randint(0,10)
    request_rate = random.randint(10,1500)
    pods = random.randint(1,10)

    service = random.choice(services)

    # critical mapping
    if service in ["patient_monitoring","emergency"]:
        service_type = "critical"
    else:
        service_type = "non_critical"

    # predicted load formula
    predicted_load = (
        0.5*cpu +
        0.3*memory +
        0.2*(latency/2) +
        0.1*request_rate/50
    )

    # =============================
    # INTELLIGENT LABELING LOGIC
    # =============================

    # --- CRITICAL SERVICE RULES ---
    if service_type == "critical":

        if cpu > 70 or latency > 200 or request_rate > 800:
            action = "scale_up"

        elif cpu < 30 and request_rate < 150 and pods > 2:
            action = "scale_down"

        else:
            action = "stable"

    # --- NON CRITICAL RULES ---
    else:

        if cpu > 85 or latency > 300:
            action = "scale_up"

        elif cpu < 25 and request_rate < 80:
            action = "scale_down"

        else:
            action = "stable"

    # =============================
    # HARD SPIKE SCENARIOS
    # =============================
    if random.random() < 0.08:
        cpu = random.randint(85,100)
        request_rate = random.randint(900,2000)
        latency = random.randint(200,500)
        action = "scale_up"

    # =============================
    # NIGHT LOW LOAD
    # =============================
    if random.random() < 0.1:
        cpu = random.randint(1,20)
        request_rate = random.randint(1,50)
        latency = random.randint(20,80)
        action = "scale_down"

    # =============================
    # POD SATURATION
    # =============================
    if pods >= 8 and cpu > 70:
        action = "scale_up"

    if pods >= 8 and service_type == "non_critical":
        action = "scale_down"

    # =============================
    # FAILURE CASE
    # =============================
    if errors > 6:
        action = "scale_up"

    # =============================
    rows.append([
        cpu,
        memory,
        latency,
        errors,
        request_rate,
        pods,
        round(predicted_load,2),
        service,
        service_type,
        action
    ])

# =============================
# SAVE CSV
# =============================
df = pd.DataFrame(rows, columns=[
    "cpu_percent",
    "memory_percent",
    "latency_ms",
    "error_count",
    "request_rate",
    "active_pods",
    "predicted_load",
    "service",
    "service_type",
    "action"
])

df.to_csv("k8s_autoscale_training_dataset.csv", index=False)

print("✅ Dataset created: k8s_autoscale_training_dataset.csv")
print("Rows:", len(df))