import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.mock_data import get_graph, reset_graph
from app.graph_engine import assess_mule_topology

client = TestClient(app)


def test_graph_population():
    reset_graph()
    G = get_graph()
    assert G.number_of_nodes() == 60
    
    clean_nodes = [n for n, d in G.nodes(data=True) if not d.get("is_mule", False)]
    mule_nodes = [n for n, d in G.nodes(data=True) if d.get("is_mule", False)]
    
    # 45 clean nodes, 15 mule nodes (1 victim + 3 L1 + 6 L2 + 1 Hub + 4 Smurf = 15 total in mule ring)
    # Note: victim is clean/victim (is_mule=False, risk_tier=VICTIM)
    # 44 pure clean + 1 victim = 45 non-mule nodes, 14 mule nodes + 1 hub = 15 mule ring accounts
    assert len(G.nodes()) == 60
    assert "victim_01@upi" in G
    assert "mule_L1_01@upi" in G
    assert "mule_L2_01@upi" in G
    assert "aggregator_hub_01@upi" in G


def test_topology_assessment_mule():
    res = assess_mule_topology("mule_L1_01@upi", 25000.0)
    assert res["graph_risk_score"] >= 0.5
    assert res["is_mule_cluster"] is True
    assert len(res["cluster_nodes"]) > 0


def test_topology_assessment_clean_merchant():
    res = assess_mule_topology("merchant_01@okhdfcbank", 500.0)
    assert res["graph_risk_score"] < 0.4
    assert res["is_mule_cluster"] is False


def test_coercion_dual_layer_high_lockout():
    # Coercion active + High graph risk mule receiver -> HIGH / LOCKOUT_3_MIN
    payload = {
        "sender_vpa": "victim_01@upi",
        "receiver_vpa": "mule_L1_01@upi",
        "amount": 25000.0,
        "telemetry": {
            "is_call_active": True,
            "is_screen_shared": False,
            "clipboard_age_sec": 12.5
        }
    }
    response = client.post("/api/v1/assess-risk", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] == "HIGH"
    assert data["action"] == "LOCKOUT_3_MIN"
    assert data["coercion_detected"] is True
    assert "Active phone call/screen share" in data["reason"]


def test_graph_risk_only_medium_warn():
    # No coercion + High graph risk mule receiver -> MEDIUM / WARN
    payload = {
        "sender_vpa": "victim_01@upi",
        "receiver_vpa": "mule_L1_02@upi",
        "amount": 25000.0,
        "telemetry": {
            "is_call_active": False,
            "is_screen_shared": False,
            "clipboard_age_sec": 0.0
        }
    }
    response = client.post("/api/v1/assess-risk", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] == "MEDIUM"
    assert data["action"] == "WARN"
    assert "rapid multi-hop" in data["reason"]


def test_clean_transaction_low_pass():
    # Clean merchant + No coercion -> LOW / PASS
    payload = {
        "sender_vpa": "user_01@okaxis",
        "receiver_vpa": "merchant_01@okhdfcbank",
        "amount": 450.0,
        "telemetry": {
            "is_call_active": False,
            "is_screen_shared": False,
            "clipboard_age_sec": 0.0
        }
    }
    response = client.post("/api/v1/assess-risk", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] == "LOW"
    assert data["action"] == "PASS"


def test_network_graph_endpoint():
    response = client.get("/api/v1/network-graph")
    assert response.status_code == 200
    data = response.json()
    assert data["total_nodes"] == 60
    assert data["total_edges"] > 0
    assert len(data["nodes"]) == 60
    assert len(data["links"]) > 0


def test_dashboard_and_static_routes():
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "RAKSHAM" in res_root.text

    res_css = client.get("/style.css")
    assert res_css.status_code == 200

    res_js = client.get("/app.js")
    assert res_js.status_code == 200


def test_dataset_presets_endpoint():
    res = client.get("/api/v1/presets")
    assert res.status_code == 200
    presets = res.json()
    assert len(presets) >= 4
    preset_ids = [p["id"] for p in presets]
    assert "safe_merchant" in preset_ids
    assert "scam_mule_coerced" in preset_ids
    assert "scam_mule_nocall" in preset_ids
    assert "cashout_hub" in preset_ids


def test_quantum_optimization_endpoint():
    res = client.post("/api/v1/quantum-optimize")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "QUANTUM_CONVERGED"
    assert data["qubits_used"] > 0
    assert data["circuit_depth"] > 0
    assert data["quantum_state_fidelity"] > 0.8
    assert "mule_cluster_nodes" in data


def test_quantum_telemetry_endpoint():
    res = client.get("/api/v1/quantum-telemetry")
    assert res.status_code == 200
    data = res.json()
    assert "qubits_used" in data
    assert "circuit_depth" in data
    assert "quantum_state_fidelity" in data


def test_assess_risk_with_quantum_payload():
    payload = {
        "sender_vpa": "victim_01@upi",
        "receiver_vpa": "mule_L1_01@upi",
        "amount": 25000.0,
        "telemetry": {
            "is_call_active": True,
            "is_screen_shared": False,
            "clipboard_age_sec": 4.5
        }
    }
    response = client.post("/api/v1/assess-risk", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["risk_level"] == "HIGH"
    assert data["action"] == "LOCKOUT_3_MIN"
    assert data["quantum_telemetry"] is not None
    assert data["quantum_telemetry"]["qubits_used"] > 0
    assert data["quantum_telemetry"]["quantum_mule_score"] > 0.5


def test_upload_dataset_csv():
    csv_content = (
        "tx_id,step,timestamp_sec,source_vpa,target_vpa,amount,tx_type,dwell_time_sec,is_fraud,is_flagged_fraud,source_balance_before,source_balance_after,target_balance_before,target_balance_after,source_account_age_hours,target_account_age_hours\n"
        "TXN_001,1,1700000000,test_user@upi,test_mule@upi,5000.0,P2P,30.0,1,1,10000.0,5000.0,0.0,5000.0,2400.0,12.0\n"
    )
    files = {"file": ("test_transactions.csv", csv_content, "text/csv")}
    res = client.post("/api/v1/upload-dataset", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "DATASET_LOADED_SUCCESS"
    assert data["quantum_telemetry"]["qubits_used"] > 0

    # Reset back to full dataset for normal test state
    client.post("/api/v1/reset-graph")


def test_get_transactions_endpoint():
    client.post("/api/v1/reset-graph")
    res = client.get("/api/v1/transactions")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["total"] > 0
    assert len(data["transactions"]) == data["total"]
    first = data["transactions"][0]
    assert "tx_id" in first
    assert "source_vpa" in first
    assert "target_vpa" in first
    assert "amount" in first


def test_batch_verify_endpoint():
    client.post("/api/v1/reset-graph")
    res = client.post("/api/v1/batch-verify")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "BATCH_VERIFIED"
    assert data["total_transactions"] > 0
    assert data["fraud_detected_count"] > 0
    assert data["clean_passed_count"] > 0
    assert len(data["results"]) == data["total_transactions"]


def test_datasheet_records_alias_endpoint():
    client.post("/api/v1/reset-graph")
    res = client.get("/api/v1/datasheet-records")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["total"] > 0
    assert len(data["transactions"]) > 0


def test_inspect_datasheet_alias_endpoint():
    csv_content = (
        "tx_id,step,timestamp_sec,source_vpa,target_vpa,amount,tx_type,dwell_time_sec,is_fraud,is_flagged_fraud,source_balance_before,source_balance_after,target_balance_before,target_balance_after,source_account_age_hours,target_account_age_hours\n"
        "TXN_002,1,1700000000,test_user@upi,test_mule@upi,5000.0,P2P,30.0,1,1,10000.0,5000.0,0.0,5000.0,2400.0,12.0\n"
    )
    files = {"file": ("test_transactions.csv", csv_content, "text/csv")}
    res = client.post("/api/v1/inspect-datasheet", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "DATASET_LOADED_SUCCESS"
    client.post("/api/v1/reset-graph")





