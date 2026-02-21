import requests
import subprocess
import time
import random

# ============================================
# 🔴 CHANGE THIS PORT EVERY TIME YOU RUN:
# run → minikube service ai-service
# copy 127.0.0.1 URL
# ============================================
MODEL_API = "http://127.0.0.1:44073/predict"

DEPLOYMENT_NAME = "ai-self-healing"

# label encodings (same as training)
service_map = {
    "analytics":0,
    "appointments":1,
    "cctv":2,
    "emergency":3,
    "lab_report":4,
    "patient_monitoring":5,
    "pharmacy":6,
    "website":7
}

type_map = {
    "critical":0,
    "non_critical":1
}

# ============================================
# Generate fake metrics
# ============================================
def generate_metrics():
    cpu = random.randint(10,95)
    memory = random.randint(10,95)
    latency = random.randint(20,300)
    errors = random.randint(0,5)
    request_rate = random.randint(50,1200)
    pods = random.randint(2,10)

    service = "patient_monitoring"
    service_type = "critical"

    predicted_load = 0.5*cpu + 0.3*memory + 0.2*(latency/2)

    return {
        "cpu_percent": cpu,
        "memory_percent": memory,
        "latency_ms": latency,
        "error_count": errors,
        "request_rate": request_rate,
        "active_pods": pods,
        "predicted_load": predicted_load,
        "service": service,
        "service_type": service_type,
        "service_encoded": service_map[service],
        "service_type_encoded": type_map[service_type]
    }

# ============================================
# Call LSTM model
# ============================================
def get_prediction(metrics):
    try:
        feature_vector = [
            metrics["cpu_percent"],
            metrics["memory_percent"],
            metrics["latency_ms"],
            metrics["error_count"],
            metrics["request_rate"],
            metrics["active_pods"],
            metrics["predicted_load"],
            metrics["service_encoded"],
            metrics["service_type_encoded"]
        ]

        sequence = [feature_vector]*10
        payload = {"sequence": sequence}

        res = requests.post(MODEL_API, json=payload, timeout=10)

        print("🔎 Raw API response:", res.text)

        data = res.json()
        return data["predicted_action"]

    except Exception as e:
        print("❌ Model API error:", e)
        return None

# ============================================
# Kubernetes scaling
# ============================================
def scale_deployment(action):

    if action == "scale_up":
        print("⚡ Scaling UP to 6 pods")
        subprocess.run([
            "kubectl","scale","deployment",DEPLOYMENT_NAME,"--replicas=6"
        ])

    elif action == "scale_down":
        print("📉 Scaling DOWN to 2 pods")
        subprocess.run([
            "kubectl","scale","deployment",DEPLOYMENT_NAME,"--replicas=2"
        ])

    else:
        print("🟢 Stable - no scaling")

# ============================================
# MAIN LOOP
# ============================================
print("\n🧠 AI Kubernetes Orchestrator Started...\n")

while True:
    metrics = generate_metrics()
    print("📊 Metrics:", metrics)

    action = get_prediction(metrics)

    if action:
        print("🤖 AI Decision:", action)
        scale_deployment(action)

    print("--------------------------------------------------")
    time.sleep(8)
