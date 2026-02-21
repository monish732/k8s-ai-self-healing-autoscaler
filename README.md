# 🚀 AI Self-Healing Health Service (Kubernetes Autoscaler)

An AI-powered Kubernetes self-healing system that dynamically manages Critical and Non-Critical microservices using real-time metrics and predictive scaling.

This project demonstrates intelligent resource prioritization inside a Kubernetes cluster using:

- AI-based prediction engine
- Live metrics monitoring
- Metrics-server tuning
- Load simulation
- Docker + Minikube deployment
- Real-time scaling observation

------------------------------------------------------------

🏗️ PROJECT STRUCTURE

k8s-ai-autoscaler/
│
├── model/
│   └── hf_deploy/
│       ├── deployment.yaml
│       ├── service.yaml
│       ├── critical-service.yaml
│       ├── noncritical-service.yaml
│       ├── live_metrics_sender.py
│       ├── predictor.py
│       ├── Dockerfile
│       └── requirements.txt
│
├── orchestrator/
│   └── ai_orchestrator.py
│
└── README.md

------------------------------------------------------------

🛠️ PREREQUISITES

- Docker Desktop (Running)
- Minikube
- kubectl
- Python 3
- Ubuntu / WSL recommended

------------------------------------------------------------

🚀 STEP-BY-STEP SETUP GUIDE

1️⃣ Start Kubernetes Cluster

Open Terminal 1:

minikube start --driver=docker
minikube addons enable metrics-server


2️⃣ Build Docker Image (If Rebuilding)

eval $(minikube docker-env)
docker build -t ai-self-healing .


3️⃣ Fix Metrics Server (Required for kubectl top)

Enable insecure TLS:

kubectl patch deployment metrics-server -n kube-system \
--type='json' \
-p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--kubelet-insecure-tls"}]'

Set metrics resolution to 15 seconds:

kubectl patch deployment metrics-server -n kube-system \
--type='json' \
-p='[{"op":"add","path":"/spec/template/spec/containers/0/args/-","value":"--metric-resolution=15s"}]'


4️⃣ Deploy Services

cd model/hf_deploy

kubectl apply -f deployment.yaml
kubectl apply -f critical-service.yaml
kubectl apply -f noncritical-service.yaml
kubectl apply -f service.yaml

Verify:

kubectl get pods
kubectl top pods


5️⃣ Access AI Service

minikube service ai-service

Copy the generated URL.

Example:
http://127.0.0.1:35863

Update this URL inside:

live_metrics_sender.py

Example:
BASE_URL = "http://127.0.0.1:35863"


------------------------------------------------------------

🧪 LOAD TESTING & MONITORING

Terminal 2 — Critical Service

minikube service critical-service


Terminal 3 — Non-Critical Service

minikube service noncritical-service


Terminal 4 — Live CPU Monitoring

watch -n 1 kubectl top pods


Terminal 5 — Start AI Metrics Sender

cd model/hf_deploy
python3 live_metrics_sender.py


------------------------------------------------------------

Manual Load Generation

Replace URL with either Critical or Non-Critical service URL:

while true; do 
curl http://127.0.0.1:36373/predict \
-X POST \
-H "Content-Type: application/json" \
-d '{"features":[80,70,200,1,800,5,80,5,0]}'; 
sleep 0.1; 
done

Modify the URL to test:
- Critical service → to stress critical workload
- Non-Critical service → to stress non-critical workload

------------------------------------------------------------

🎯 WHAT THIS PROJECT DEMONSTRATES

- Intelligent Kubernetes workload management
- AI-driven service prioritization
- Real-time metrics-based scaling
- Critical vs Non-Critical traffic control
- Self-healing microservice orchestration

------------------------------------------------------------

🧠 CORE COMPONENTS

AI Predictor          → Predicts system stress  
Metrics Sender        → Sends live cluster metrics  
Critical Service      → High priority microservice  
Non-Critical Service  → Lower priority workload  
Metrics Server        → Provides real-time CPU data  
Orchestrator          → Decision-making logic  

------------------------------------------------------------

📌 IMPORTANT NOTES

- Keep terminal open when using `minikube service`
- Docker driver requires tunnel to stay active
- Metrics-server patch required in WSL/Linux
- Ensure Docker Desktop is running before cluster start

------------------------------------------------------------

🔥 FUTURE IMPROVEMENTS

- Horizontal Pod Autoscaler integration
- Prometheus + Grafana dashboard
- Reinforcement learning-based scaling
- Multi-node cluster simulation
- Cloud deployment (EKS / GKE)


------------------------------------------------------------

🏗️ ARCHITECTURE DIAGRAM

Below shows how the AI Self-Healing Kubernetes system works.

                    ┌────────────────────────────┐
                    │        User / Load         │
                    │   (Manual / Auto Traffic)  │
                    └────────────┬───────────────┘
                                 │
                                 ▼
                    ┌────────────────────────────┐
                    │     Kubernetes Cluster     │
                    │        (Minikube)          │
                    └────────────┬───────────────┘
                                 │
          ┌──────────────────────┼──────────────────────┐
          │                      │                      │
          ▼                      ▼                      ▼

 ┌────────────────┐   ┌──────────────────┐   ┌──────────────────┐
 │ Critical App   │   │ Non-Critical App │   │   AI Service     │
 │ (High Priority)│   │ (Low Priority)   │   │ (Prediction API) │
 └──────┬─────────┘   └────────┬─────────┘   └────────┬─────────┘
        │                      │                      │
        │ CPU/Memory usage    │ CPU/Memory usage     │
        └──────────────┬──────┴──────────────┬──────┘
                       ▼                     ▼
                ┌────────────────────────────────┐
                │        Metrics Server          │
                │ (kubectl top / live metrics)   │
                └──────────────┬─────────────────┘
                               ▼
                 ┌────────────────────────────┐
                 │   live_metrics_sender.py   │
                 │ Sends metrics → AI model   │
                 └──────────────┬─────────────┘
                                ▼
                 ┌────────────────────────────┐
                 │      AI Predictor Model    │
                 │  (Stress / Load Decision) │
                 └──────────────┬─────────────┘
                                ▼
                 ┌────────────────────────────┐
                 │      AI Orchestrator       │
                 │ Scale / Control Services   │
                 └────────────────────────────┘

------------------------------------------------------------

⚙️ WORKFLOW EXPLANATION

1. User sends traffic to services
2. Critical & Non-Critical pods consume CPU
3. Metrics-server collects live CPU usage
4. live_metrics_sender sends metrics to AI model
5. AI predicts system stress
6. Orchestrator decides scaling/prioritization
7. Kubernetes adjusts workload dynamically

------------------------------------------------------------

🎯 KEY IDEA

If system load increases:
→ Critical service gets priority
→ Non-critical service can be throttled
→ AI predicts before failure
→ System becomes self-healing

------------------------------------------------------------

👨‍💻 Author

Monish C 