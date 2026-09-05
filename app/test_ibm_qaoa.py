print("SCRIPT STARTED", flush=True)

import os
from dotenv import load_dotenv

load_dotenv() 

from qiskit import QuantumCircuit
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler


# ============================================================
# 1. CONNECT TO IBM QUANTUM
# ============================================================

load_dotenv()

token = os.getenv("IBM_QUANTUM_TOKEN")
instance = os.getenv("IBM_QUANTUM_INSTANCE", "")

print("TOKEN FOUND:", bool(token))
print("INSTANCE FOUND:", bool(instance)) 

try:
    service = QiskitRuntimeService(
        channel="ibm_quantum_platform",
        token=token,
        instance=instance,
    )
except Exception as error:
    raise RuntimeError(
        "Could not connect to IBM Quantum. Check IBM_QUANTUM_TOKEN and "
        "IBM_QUANTUM_INSTANCE."
    ) from error


# ============================================================
# 2. SELECT A REAL IBM QUANTUM BACKEND
# ============================================================

try:
    backend = service.least_busy(
        simulator=False,
        operational=True,
        min_num_qubits=2,
    )
except Exception as error:
    raise RuntimeError("No operational IBM Quantum backend with at least 2 qubits was found.") from error

print("\n========================================")
print("IBM QUANTUM CONNECTION")
print("========================================")

print("Backend:", backend.name)
print("Qubits:", backend.num_qubits)


# ============================================================
# 3. CREATE A SIMPLE QUANTUM CIRCUIT
# ============================================================

qc = QuantumCircuit(2)

qc.h(0)
qc.cx(0, 1)

qc.measure_all()

print("\n========================================")
print("ORIGINAL CIRCUIT")
print("========================================")

print(qc)


# ============================================================
# 4. TRANSPILE FOR IBM HARDWARE
# ============================================================

pm = generate_preset_pass_manager(
    backend=backend,
    optimization_level=1
)

isa_circuit = pm.run(qc)

print("\n========================================")
print("TRANSPILED CIRCUIT")
print("========================================")

print(isa_circuit)


# ============================================================
# 5. RUN ON REAL IBM QUANTUM HARDWARE
# ============================================================

sampler = Sampler(mode=backend)

job = sampler.run(
    [isa_circuit],
    shots=100
)

print("\n========================================")
print("JOB SUBMITTED")
print("========================================")

print("Job ID:", job.job_id())
print("Status:", job.status())


# ============================================================
# 6. WAIT FOR RESULT
# ============================================================

result = job.result()

print("\n========================================")
print("RESULT RECEIVED")
print("========================================")

pub_result = result[0]

bitstrings = pub_result.data.meas.get_bitstrings()

print("First 20 measurements:")

for bitstring in bitstrings[:20]:
    print(bitstring)

print("\nTotal measurements:", len(bitstrings))

print("\n========================================")
print("IBM QUANTUM TEST COMPLETE")
print("========================================")
