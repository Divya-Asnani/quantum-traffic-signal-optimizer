from qiskit_ibm_runtime import QiskitRuntimeService

service = QiskitRuntimeService(
    channel="ibm_quantum_platform",
    token="b_tBvnvqCiQsJZsemOgB0nwGYumaycGixVK1M4fAKXnG",
    instance="crn:v1:bluemix:public:quantum-computing:us-east:a/9652be921ef4405bbbacef0c8517170d:cf406170-4fcf-4dd8-bdf9-a244f0ba8ec5::"
)

print("\nConnected to IBM Quantum successfully!\n")

backends = service.backends(
    simulator=False,
    operational=True
)

print("Available IBM Quantum backends:\n")

for backend in backends:
    print(
        f"{backend.name} | "
        f"Qubits: {backend.num_qubits}"
    )