from fastapi import FastAPI
import torch
import numpy as np
import pickle
from huggingface_hub import hf_hub_download

app = FastAPI()

print("\n⬇ Downloading model from HuggingFace...\n")

# ================================
# DOWNLOAD MODEL FROM HF
# ================================
model_path = hf_hub_download(
    repo_id="Hariprasath5128/self_healing",
    filename="best_lstm_model.pth"
)

scaler_path = hf_hub_download(
    repo_id="Hariprasath5128/self_healing",
    filename="scaler.pkl"
)

encoder_path = hf_hub_download(
    repo_id="Hariprasath5128/self_healing",
    filename="label_encoders.pkl"
)

print("✅ Model downloaded")

# ================================
# LOAD MODEL
# ================================
device = torch.device("cpu")

class HealthcareLSTM(torch.nn.Module):
    def __init__(self,input_size=9,hidden_size=64,num_layers=2,num_classes=3):
        super().__init__()
        self.lstm = torch.nn.LSTM(input_size,hidden_size,num_layers,
                                  batch_first=True,bidirectional=True)
        self.fc1 = torch.nn.Linear(hidden_size*2,32)
        self.relu = torch.nn.ReLU()
        self.fc2 = torch.nn.Linear(32,num_classes)

    def forward(self,x):
        out,_ = self.lstm(x)
        last = out[:,-1,:]
        out = self.relu(self.fc1(last))
        out = self.fc2(out)
        return out

model = HealthcareLSTM()
model.load_state_dict(torch.load(model_path,map_location=device))
model.eval()

scaler = pickle.load(open(scaler_path,"rb"))
encoders = pickle.load(open(encoder_path,"rb"))

print("🚀 MODEL READY\n")

# ====================================
# RECEIVE LIVE FEATURES FROM EXTRACTOR
# ====================================
@app.post("/predict")
def predict(data: dict):

    feature_vector = data["features"]

    # create sequence
    sequence = [feature_vector]*10

    seq = np.array(sequence)
    seq = scaler.transform(seq.reshape(-1,9)).reshape(1,10,9)

    tensor = torch.FloatTensor(seq)

    with torch.no_grad():
        out = model(tensor)
        probs = torch.softmax(out, dim=1).numpy()[0]
        pred = probs.argmax()

    action = encoders["action"].inverse_transform([pred])[0]
    confidence = float(np.max(probs))

    # PRINT BOTH INPUT + OUTPUT
    print("\n================ MODEL INPUT =================")
    print("Feature Vector:", feature_vector)

    print("\n🤖 MODEL OUTPUT")
    print("Action      :", action)
    print("Confidence  :", confidence)
    print("==============================================\n")

    return {
        "predicted_action": action,
        "confidence": confidence
    }
