from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


class DeviceTelemetry(BaseModel):
    is_call_active: bool = Field(
        default=False,
        description="Whether a cellular/VoIP call is currently active on the device"
    )
    is_screen_shared: bool = Field(
        default=False,
        description="Whether screen sharing/remote access tools (AnyDesk, TeamViewer) are active"
    )
    clipboard_age_sec: float = Field(
        default=0.0,
        ge=0.0,
        description="Seconds elapsed since receiver VPA/amount was copied into clipboard"
    )


class TransactionRequest(BaseModel):
    sender_vpa: str = Field(..., examples=["victim_01@upi", "rahul.sharma@okhdfcbank"])
    receiver_vpa: str = Field(..., examples=["mule_L1_01@upi", "merchant_grocery@okicici"])
    amount: float = Field(..., gt=0.0, examples=[25000.0, 500.0])
    telemetry: DeviceTelemetry = Field(default_factory=DeviceTelemetry)


class GraphSnapshot(BaseModel):
    graph_risk_score: float = Field(..., ge=0.0, le=1.0)
    is_mule_cluster: bool
    cluster_nodes: List[str] = Field(default_factory=list)
    cluster_edges: List[Dict[str, Any]] = Field(default_factory=list)
    factors: Optional[Dict[str, Any]] = Field(default_factory=dict)


class QuantumTelemetry(BaseModel):
    qubits_used: int = Field(default=8, description="Number of qubits allocated in statevector circuit")
    circuit_depth: int = Field(default=14, description="Quantum variational circuit depth")
    quantum_state_fidelity: float = Field(default=0.984, description="Quantum state fidelity / probability overlap")
    hamiltonian_energy: float = Field(default=-4.821, description="Optimal expectation value <H_C>")
    quantum_mule_score: float = Field(default=0.0, description="Quantum ring coherence anomaly metric (0.0 to 1.0)")
    mule_path: List[str] = Field(default_factory=list, description="Optimal quantum cut path")
    execution_time_ms: float = Field(default=12.4, description="QPU statevector simulation time in ms")


class AssessmentResponse(BaseModel):
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    action: Literal["PASS", "WARN", "LOCKOUT_3_MIN"]
    coercion_detected: bool
    reason: str
    graph_snapshot: GraphSnapshot
    quantum_telemetry: Optional[QuantumTelemetry] = None



# Models for D3 / Cytoscape.js Network Graph Visualizer
class NetworkNode(BaseModel):
    id: str
    label: str
    risk_tier: Literal["CLEAN", "SUSPECT", "MULE_L1", "MULE_L2", "HUB", "VICTIM"]
    created_hours_ago: float
    in_degree: int
    out_degree: int
    flagged_history: int
    is_mule: bool
    x: Optional[float] = None
    y: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class NetworkEdge(BaseModel):
    source: str
    target: str
    amount: float
    dwell_time_sec: Optional[float] = None
    timestamp_sec: Optional[float] = None
    tx_id: Optional[str] = None


class NetworkGraphResponse(BaseModel):
    nodes: List[NetworkNode]
    links: List[NetworkEdge]
    total_nodes: int
    total_edges: int
    mule_nodes_count: int
    clean_nodes_count: int
