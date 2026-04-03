# 🛡️ QuantumCipherSim SOC Dashboard

**QuantumCipherSim** is a high-fidelity Quantum Key Distribution (QKD) telemetry and AI-driven SOC (Security Operations Center) dashboard. It monitors quantum channels in real-time, detecting eavesdropping (Eve) and deploying active mitigation strategies like Privacy Amplification (BB84) and Entanglement Routing (E91).

![Dashboard Preview](https://github.com/MithileshK05/quantumciphersim/blob/main/frontend/src/assets/preview.png?raw=true)

---

## 🚀 Core Features

### 1. **Cinematic 3D Physical Layer**
- **Refractive Glass Fiber**: A physics-accurate `<MeshTransmissionMaterial>` fiber optic tube with real-time light refraction (`ior: 1.5`) and chromatic aberration.
- **Dynamic Particle Streams**: High-density quantum-foam sparkles and photon trails that react instantly to channel health.
- **State-Reactive Environment**: An infinite grid space that shifts based on simulation states (e.g., Red for compromise, Purple for active defense).

### 2. **AI-Driven Threat Detection**
- **ML Pipeline**: A Gradient Boosting classifier monitors QBER (Quantum Bit Error Rate) and Key Rate to identify intercept-resend attacks with high confidence.
- **HUD HUD HUD**: Real-time HUD cards with neon-pulsing status indicators synchronized with a live streaming Recharts telemetry graph.

### 3. **Unified Mitigation Engine**
- **BB84 (Privacy Amplification)**: Automatically compresses keys and resets QBER to safe baselines during an attack.
- **E91 (Entanglement Routing)**: Switches to a shielded entanglement wave (visualized as intertwined purple sine-ribbons) to bypass eavesdroppers.

---

## 🛠️ Tech Stack

- **Frontend**: React (Vite), TailwindCSS, Three.js (`@react-three/fiber`, `@react-three/drei`), Recharts.
- **Backend**: FastAPI (Python), Uvicorn.
- **Machine Learning**: Scikit-Learn (Gradient Boosting), Joblib.
- **Simulation**: Qiskit (Aer) for backend quantum circuit emulation.

---

## 📦 Setup & Installation

### Prerequisites
- **Node.js** (v18+)
- **Python** (3.10+)
- **NPM**

### 1. Backend Setup
```bash
# Navigate to root
pip install -r requirements.txt

# Start the FastAPI server
python -m uvicorn backend.main:app --reload --port 8000
```

### 2. Frontend Setup
```bash
# Navigate to frontend folder
cd frontend
npm install

# Start the Vite dev server
npm run dev
```

### 3. Access
The dashboard will be live at `http://localhost:5173/sim`.

---

## 🔬 Operational Modes

| Mode | Visual Indicator | Status Message |
| :--- | :--- | :--- |
| **Secure** | Cyan Photons | `SECURE` |
| **Compromised** | Red 3D Channel | `⚠ CHANNEL COMPROMISED` |
| **BB84 PA Active** | Purple Pulse | `⚡ PRIVACY AMPLIFICATION ACTIVE` |
| **E91 Attacked** | Orange Aura | `⚠ BELL TEST VIOLATION` |
| **E91 Shielded** | Dual Purple Ribbons | `🛡 ENTANGLEMENT SHIELD ACTIVE` |

---

## 📂 Repository Structure

- `frontend/`: React components and Three.js visualization.
- `backend/`: FastAPI routers and metrics simulation logic.
- `ml/`: Pre-trained models and inference pipeline.
- `tools/`: Diagnostic scripts (`verify_backend.py`, `bb84_simulator.py`).

---

## 📜 License
MIT License. Created by [MithileshK05](https://github.com/MithileshK05).
