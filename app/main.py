import os
import shutil
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.schemas import (
    TransactionRequest,
    AssessmentResponse,
    GraphSnapshot,
    QuantumTelemetry,
    NetworkGraphResponse,
    NetworkNode,
    NetworkEdge
)
from app.graph_engine import assess_mule_topology
from app.mock_data import get_graph, reset_graph
from app.dataset_pipeline import DATASET_CSV_PATH, reset_dataset_pipeline, get_dataset_graph, get_dataset_transactions
from app.quantum_engine import get_quantum_engine

app = FastAPI(
    title="RAKSHAM PS2 - Quantum Graph Analysis & UPI Coercion Engine",
    description="Dual-layer topological QAOA quantum statevector analysis & device telemetry coercion recognition engine.",
    version="2.0.0"
)

# Enable CORS for frontend visualizers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if not os.path.exists(STATIC_DIR):
    STATIC_DIR = os.path.abspath("static")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def serve_dashboard():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "engine": "RAKSHAM PS2 Engine",
        "status": "ONLINE",
        "docs_url": "/docs",
        "graph_endpoint": "/api/v1/network-graph",
        "assess_endpoint": "/api/v1/assess-risk"
    }


@app.get("/index.html")
def serve_index_html():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="index.html not found")



@app.get("/style.css")
def serve_css():
    css_path = os.path.join(STATIC_DIR, "style.css")
    if os.path.exists(css_path):
        return FileResponse(css_path, media_type="text/css")
    raise HTTPException(status_code=404, detail="style.css not found")


@app.get("/styles.css")
def serve_styles_css():
    css_path = os.path.join(STATIC_DIR, "styles.css")
    if not os.path.exists(css_path):
        css_path = os.path.join(STATIC_DIR, "style.css")
    if os.path.exists(css_path):
        return FileResponse(css_path, media_type="text/css")
    raise HTTPException(status_code=404, detail="styles.css not found")



@app.get("/app.js")
def serve_js():
    js_path = os.path.join(STATIC_DIR, "app.js")
    if os.path.exists(js_path):
        return FileResponse(js_path, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="app.js not found")


@app.get("/favicon.ico")
def serve_favicon():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"), status_code=204)



@app.get("/health")
def health_check():
    graph = get_graph()
    q_engine = get_quantum_engine()
    return {
        "status": "healthy",
        "total_nodes": graph.number_of_nodes(),
        "total_edges": graph.number_of_edges(),
        "quantum_engine_status": q_engine.last_telemetry.get("status", "READY")
    }


@app.post("/api/v1/assess-risk", response_model=AssessmentResponse)
def assess_risk(request: TransactionRequest):
    """
    Evaluates risk on a prospective UPI transaction by cross-referencing
    device telemetry (active phone calls, screen sharing, clipboard tampering)
    with NetworkX 2-hop graph dispersal topology anomalies and QAOA Quantum Statevector Analysis.
    """
    graph = get_graph()
    topology_result = assess_mule_topology(
        target_vpa=request.receiver_vpa,
        amount=request.amount
    )
    graph_risk_score = topology_result["graph_risk_score"]

    # Execute QAOA Quantum Graph Solver on receiver neighborhood
    q_engine = get_quantum_engine()
    q_result = q_engine.solve_mule_cluster(graph, target_vpa=request.receiver_vpa)
    quantum_mule_score = q_result["quantum_mule_score"]

    telemetry = request.telemetry
    active_coercion_vector = telemetry.is_call_active or telemetry.is_screen_shared

    # Combined Hybrid Anomaly Score
    effective_risk_score = round(0.6 * graph_risk_score + 0.4 * quantum_mule_score, 3)

    # Quantum & Telemetry Decision Matrix
    if active_coercion_vector and (effective_risk_score > 0.5 or quantum_mule_score > 0.5):
        risk_level = "HIGH"
        action = "LOCKOUT_3_MIN"
        coercion_detected = True
        reason = "Active phone call/screen share detected during transfer to newly registered mule network. Quantum Ring Clustering confirmed active mule dispersal."
    elif effective_risk_score > 0.6 or quantum_mule_score > 0.6:
        risk_level = "MEDIUM"
        action = "WARN"
        coercion_detected = bool(active_coercion_vector)
        reason = "Receiver account shows rapid multi-hop fund dispersal patterns. Quantum statevector analysis identified smurfing cluster."
    else:
        risk_level = "LOW"
        action = "PASS"
        coercion_detected = bool(active_coercion_vector)
        reason = "Transaction parameters and receiver graph topology are within normal parameters. Quantum graph partitioning verified benign cluster."


    graph_snapshot = GraphSnapshot(
        graph_risk_score=effective_risk_score,
        is_mule_cluster=topology_result["is_mule_cluster"] or q_result["is_mule_cluster"],
        cluster_nodes=list(set(topology_result["cluster_nodes"] + q_result["mule_cluster_nodes"])),
        cluster_edges=topology_result["cluster_edges"],
        factors={
            **topology_result.get("factors", {}),
            "quantum_mule_score": quantum_mule_score,
            "quantum_state_fidelity": q_result["quantum_state_fidelity"],
            "hamiltonian_energy": q_result["hamiltonian_energy"]
        }
    )

    q_telemetry = QuantumTelemetry(
        qubits_used=q_result["qubits_used"],
        circuit_depth=q_result["circuit_depth"],
        quantum_state_fidelity=q_result["quantum_state_fidelity"],
        hamiltonian_energy=q_result["hamiltonian_energy"],
        quantum_mule_score=quantum_mule_score,
        mule_path=q_result["mule_path"],
        execution_time_ms=q_result["execution_time_ms"]
    )

    return AssessmentResponse(
        risk_level=risk_level,
        action=action,
        coercion_detected=coercion_detected,
        reason=reason,
        graph_snapshot=graph_snapshot,
        quantum_telemetry=q_telemetry
    )


@app.post("/api/v1/quantum-optimize")
def run_quantum_optimization():
    """
    Executes full QAOA Ising Hamiltonian statevector simulation across the active graph.
    Returns optimal partitioned clusters, active qubits, circuit depth, and fidelity.
    """
    graph = get_graph()
    q_engine = get_quantum_engine()
    result = q_engine.solve_mule_cluster(graph, target_vpa=None)
    return {
        "status": "QUANTUM_CONVERGED",
        "qubits_used": result["qubits_used"],
        "circuit_depth": result["circuit_depth"],
        "quantum_state_fidelity": result["quantum_state_fidelity"],
        "hamiltonian_energy": result["hamiltonian_energy"],
        "execution_time_ms": result["execution_time_ms"],
        "mule_cluster_nodes": result["mule_cluster_nodes"],
        "benign_nodes_count": len(result["benign_nodes"]),
        "mule_path": result["mule_path"]
    }


@app.get("/api/v1/quantum-telemetry")
def get_quantum_telemetry():
    """Returns the latest QPU statevector simulator metrics and telemetry."""
    q_engine = get_quantum_engine()
    return q_engine.last_telemetry


@app.post("/api/v1/inspect-datasheet")
@app.post("/api/v1/upload-dataset")
async def upload_dataset_csv(file: UploadFile = File(...)):
    """
    Uploads and parses a .csv transaction datasheet, constructs the NetworkX graph,
    and runs initial quantum graph partitioning.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only .csv files are supported")

    with open(DATASET_CSV_PATH, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Re-ingest dataset into graph pipeline
    graph = reset_dataset_pipeline()

    # Run quantum optimization on the new dataset
    q_engine = get_quantum_engine()
    q_result = q_engine.solve_mule_cluster(graph)

    return {
        "status": "DATASET_LOADED_SUCCESS",
        "filename": file.filename,
        "total_nodes": graph.number_of_nodes(),
        "total_edges": graph.number_of_edges(),
        "quantum_telemetry": {
            "qubits_used": q_result["qubits_used"],
            "circuit_depth": q_result["circuit_depth"],
            "quantum_state_fidelity": q_result["quantum_state_fidelity"],
            "hamiltonian_energy": q_result["hamiltonian_energy"],
            "execution_time_ms": q_result["execution_time_ms"],
            "mule_cluster_nodes": q_result["mule_cluster_nodes"]
        }
    }



@app.get("/api/v1/network-graph", response_model=NetworkGraphResponse)
def get_network_graph():
    """
    Returns full graph topology formatted for Cytoscape.js or D3 force-directed visualizer.
    Includes node risk tiers, coordinates, and edge transfer velocities.
    """
    graph = get_graph()
    nodes = []
    mule_count = 0
    clean_count = 0

    for node_id, data in graph.nodes(data=True):
        is_mule = data.get("is_mule", False)
        if is_mule:
            mule_count += 1
        else:
            clean_count += 1

        nodes.append(
            NetworkNode(
                id=node_id,
                label=data.get("label", node_id),
                risk_tier=data.get("risk_tier", "CLEAN"),
                created_hours_ago=data.get("created_hours_ago", 1000.0),
                in_degree=graph.in_degree(node_id),
                out_degree=graph.out_degree(node_id),
                flagged_history=data.get("flagged_history", 0),
                is_mule=is_mule,
                x=data.get("x"),
                y=data.get("y"),
                metadata={
                    "account_type": data.get("account_type", "STANDARD")
                }
            )
        )

    links = []
    for u, v, data in graph.edges(data=True):
        links.append(
            NetworkEdge(
                source=u,
                target=v,
                amount=data.get("amount", 0.0),
                dwell_time_sec=data.get("dwell_time_sec"),
                timestamp_sec=data.get("timestamp_sec"),
                tx_id=data.get("tx_id")
            )
        )

    return NetworkGraphResponse(
        nodes=nodes,
        links=links,
        total_nodes=len(nodes),
        total_edges=len(links),
        mule_nodes_count=mule_count,
        clean_nodes_count=clean_count
    )


@app.get("/api/v1/presets")
def get_dataset_presets():
    """
    Returns verified preset test cases extracted from the Prototype 2 transaction dataset.
    """
    return [
        {
            "id": "safe_merchant",
            "name": "Sharma General Store (Clean Verified Merchant)",
            "receiver_vpa": "merchant_01@okhdfcbank",
            "amount": 450.0,
            "call_active": False,
            "screen_shared": False,
            "category": "BENIGN_CLUSTER",
            "description": "Established merchant account with low risk topology and normal dwell times."
        },
        {
            "id": "scam_mule_coerced",
            "name": "Unknown Courier Refund (Quantum-Identified Mule L1 + Call Coercion)",
            "receiver_vpa": "mule_L1_01@upi",
            "amount": 25000.0,
            "call_active": True,
            "screen_shared": False,
            "category": "FRAUD_SMURFING_CLUSTER",
            "description": "High-velocity layer-1 mule dispersal ring with incoming coercion voice call."
        },
        {
            "id": "scam_mule_nocall",
            "name": "High-Velocity Mule Dispersal L1 (No Call)",
            "receiver_vpa": "mule_L1_02@upi",
            "amount": 18500.0,
            "call_active": False,
            "screen_shared": False,
            "category": "FRAUD_SMURFING_CLUSTER",
            "description": "Multi-hop smurfing dispersal account with dwell times under 60 seconds."
        },
        {
            "id": "cashout_hub",
            "name": "Terminal Cash-Out Hub (Aggregator Hub)",
            "receiver_vpa": "aggregator_hub_01@upi",
            "amount": 75000.0,
            "call_active": True,
            "screen_shared": False,
            "category": "TERMINAL_CASHOUT_HUB",
            "description": "High in-degree aggregator funneling illicit funds from multiple layer-2 mules."
        },
        {
            "id": "p2p_clean",
            "name": "Rahul Verma (Verified P2P Peer)",
            "receiver_vpa": "user_01@okhdfcbank",
            "amount": 1200.0,
            "call_active": False,
            "screen_shared": False,
            "category": "BENIGN_CLUSTER",
            "description": "Legitimate peer-to-peer individual account with long history."
        }
    ]


@app.post("/api/v1/reset-graph")
def reset_network_graph():
    """Resets the in-memory dataset topology to baseline state."""
    graph = reset_graph()
    return {
        "status": "RESET_SUCCESS",
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges()
    }


@app.get("/api/v1/transactions")
def get_transactions():
    """Returns all transactions parsed from the active dataset CSV."""
    txs = get_dataset_transactions()
    return {
        "status": "SUCCESS",
        "total": len(txs),
        "transactions": txs
    }


@app.post("/api/v1/batch-verify")
def batch_verify_transactions():
    """
    Runs dual-layer Quantum + Graph verification across all transactions in the active dataset.
    Returns overall statistics, fraud detection precision, and telemetry.
    """
    txs = get_dataset_transactions()
    graph = get_graph()
    q_engine = get_quantum_engine()
    
    verified = []
    fraud_detected = 0
    clean_passed = 0
    
    for tx in txs:
        target = tx["target_vpa"]
        amt = tx["amount"]
        is_fraud = tx["is_fraud"]
        
        topo = assess_mule_topology(target, amt)
        q_res = q_engine.solve_mule_cluster(graph, target_vpa=target)
        
        effective_risk = round(0.6 * topo["graph_risk_score"] + 0.4 * q_res["quantum_mule_score"], 3)
        predicted_fraud = effective_risk > 0.5 or q_res["quantum_mule_score"] > 0.5 or topo["is_mule_cluster"]
        
        if predicted_fraud:
            fraud_detected += 1
            risk_tier = "HIGH" if effective_risk > 0.7 else "MEDIUM"
        else:
            clean_passed += 1
            risk_tier = "LOW"
            
        verified.append({
            "tx_id": tx["tx_id"],
            "source_vpa": tx["source_vpa"],
            "target_vpa": tx["target_vpa"],
            "amount": tx["amount"],
            "tx_type": tx["tx_type"],
            "dwell_time_sec": tx["dwell_time_sec"],
            "is_ground_truth_fraud": is_fraud,
            "predicted_fraud": predicted_fraud,
            "risk_tier": risk_tier,
            "effective_risk_score": effective_risk,
            "quantum_mule_score": q_res["quantum_mule_score"],
            "hamiltonian_energy": q_res["hamiltonian_energy"]
        })
        
    return {
        "status": "BATCH_VERIFIED",
        "total_transactions": len(txs),
        "fraud_detected_count": fraud_detected,
        "clean_passed_count": clean_passed,
        "quantum_state_fidelity": q_engine.last_telemetry.get("quantum_state_fidelity", 0.984),
        "results": verified
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

