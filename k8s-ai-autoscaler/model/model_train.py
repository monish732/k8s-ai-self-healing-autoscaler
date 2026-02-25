import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from sklearn.preprocessing import StandardScaler, LabelEncoder
import pickle

print("\n🧠 LSTM TRAINING STARTED...\n")

# ===============================
# LOAD DATASET
# ===============================
df = pd.read_csv("k8s_autoscale_training_dataset.csv")
print("Dataset loaded:", df.shape)

# ===============================
# ENCODE CATEGORICAL FEATURES
# ===============================
label_encoders = {}

for col in ["service", "service_type", "action"]:
    le = LabelEncoder()
    df[col] = le.fit_transform(df[col])
    label_encoders[col] = le

# ===============================
# FEATURES AND TARGET
# ===============================
features = [
    "cpu_percent",
    "memory_percent",
    "latency_ms",
    "error_count",
    "request_rate",
    "active_pods",
    "predicted_load",
    "service",
    "service_type"
]

X = df[features].values
y = df["action"].values

# ===============================
# FEATURE SCALING
# ===============================
scaler = StandardScaler()
X = scaler.fit_transform(X)

# ===============================
# CREATE SEQUENCES FOR LSTM
# ===============================
SEQ_LEN = 10
X_seq, y_seq = [], []

for i in range(len(X) - SEQ_LEN):
    X_seq.append(X[i:i + SEQ_LEN])
    y_seq.append(y[i + SEQ_LEN])

X_seq = np.array(X_seq)
y_seq = np.array(y_seq)

print("Sequence shape:", X_seq.shape)

# ===============================
# TORCH TENSORS
# ===============================
X_tensor = torch.FloatTensor(X_seq)
y_tensor = torch.LongTensor(y_seq)

# ===============================
# MODEL DEFINITION (BiLSTM)
# ===============================
class HealthcareLSTM(nn.Module):
    def __init__(self, input_size=9, hidden_size=64, num_layers=2, num_classes=3):
        super().__init__()

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            bidirectional=True
        )

        self.fc1 = nn.Linear(hidden_size * 2, 32)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(32, num_classes)

    def forward(self, x):
        out, _ = self.lstm(x)
        last_step = out[:, -1, :]
        out = self.relu(self.fc1(last_step))
        out = self.fc2(out)
        return out

model = HealthcareLSTM()

# ===============================
# LOSS AND OPTIMIZER
# ===============================
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=0.001)

# ===============================
# TRAINING LOOP
# ===============================
EPOCHS = 30
BATCH_SIZE = 64

for epoch in range(EPOCHS):
    perm = torch.randperm(X_tensor.size(0))
    total_loss = 0

    for i in range(0, X_tensor.size(0), BATCH_SIZE):
        idx = perm[i:i + BATCH_SIZE]

        xb = X_tensor[idx]
        yb = y_tensor[idx]

        optimizer.zero_grad()
        outputs = model(xb)
        loss = criterion(outputs, yb)
        loss.backward()
        optimizer.step()

        total_loss += loss.item()

    print(f"Epoch {epoch + 1}/{EPOCHS} | Loss: {total_loss:.4f}")

# ===============================
# SAVE MODEL AND PREPROCESSORS
# ===============================
torch.save(model.state_dict(), "best_lstm_model.pth")
pickle.dump(scaler, open("scaler.pkl", "wb"))
pickle.dump(label_encoders, open("label_encoders.pkl", "wb"))

print("\n✅ TRAINING COMPLETE")
print("Saved files:")
print("- best_lstm_model.pth")
print("- scaler.pkl")
print("- label_encoders.pkl")