from typing import Dict, Any, List, Set
import networkx as nx
from app.mock_data import get_graph


def get_two_hop_neighborhood(graph: nx.DiGraph, target_vpa: str) -> Set[str]:
    """
    Extracts the full 2-hop directed neighborhood (successors and predecessors)
    around the target VPA to capture both fund origin and forward dispersal paths.
    """
    if target_vpa not in graph:
        return {target_vpa}

    nodes: Set[str] = {target_vpa}

    # 1-hop and 2-hop successors (forward fund dispersal)
    succ_1 = set(graph.successors(target_vpa))
    nodes.update(succ_1)
    for s in succ_1:
        nodes.update(graph.successors(s))

    # 1-hop and 2-hop predecessors (incoming funding sources)
    pred_1 = set(graph.predecessors(target_vpa))
    nodes.update(pred_1)
    for p in pred_1:
        nodes.update(graph.predecessors(p))

    return nodes


def assess_mule_topology(target_vpa: str, amount: float = 0.0) -> Dict[str, Any]:
    """
    Inspects the 2-hop neighborhood around `target_vpa` to compute a Graph Anomaly Score (0.0 - 1.0)
    evaluating:
      a) Fan-out / Fan-in ratio (many-to-one funneling or one-to-many smurfing bursts)
      b) Dwell time heuristic & account age (< 24 hrs gives high risk)
      c) Direct/indirect connectivity to known mule rings & cash-out hubs
    
    Returns:
      {
        "graph_risk_score": float,
        "is_mule_cluster": bool,
        "cluster_nodes": list,
        "cluster_edges": list,
        "factors": dict
      }
    """
    graph = get_graph()

    # If the target VPA is completely new/unseen in the graph
    if target_vpa not in graph:
        # High suspicion for unseen receiver in fast transfer context
        return {
            "graph_risk_score": 0.65,
            "is_mule_cluster": False,
            "cluster_nodes": [target_vpa],
            "cluster_edges": [],
            "factors": {
                "account_age_penalty": 0.35,
                "unregistered_new_vpa": True,
                "dwell_time_risk": 0.0,
                "fan_ratio_risk": 0.0,
                "mule_connectivity_risk": 0.30
            }
        }

    neighbor_nodes = get_two_hop_neighborhood(graph, target_vpa)
    subgraph = graph.subgraph(neighbor_nodes)

    target_data = graph.nodes[target_vpa]
    created_hours = target_data.get("created_hours_ago", 1000.0)
    flagged_history = target_data.get("flagged_history", 0)

    # -------------------------------------------------------------
    # Factor A: Account Age Risk (Max weight: 0.30)
    # -------------------------------------------------------------
    # Fresh accounts (< 24 hours) have peak risk; decays sharply after 72 hours
    if created_hours < 24.0:
        age_risk = 0.30
    elif created_hours < 72.0:
        age_risk = 0.20
    elif created_hours < 360.0:  # < 15 days
        age_risk = 0.08
    else:
        age_risk = 0.00

    # -------------------------------------------------------------
    # Factor B: Dwell Time Heuristic (Max weight: 0.25)
    # -------------------------------------------------------------
    # Rapid pass-through (< 180 seconds between in and out funds) is a primary money mule indicator
    dwell_times = []
    for u, v, data in subgraph.edges(data=True):
        if "dwell_time_sec" in data:
            dwell_times.append(data["dwell_time_sec"])

    if dwell_times:
        min_dwell = min(dwell_times)
        avg_dwell = sum(dwell_times) / len(dwell_times)
        if min_dwell < 120 or avg_dwell < 180:
            dwell_risk = 0.25
        elif min_dwell < 300 or avg_dwell < 600:
            dwell_risk = 0.15
        elif min_dwell < 1800:
            dwell_risk = 0.05
        else:
            dwell_risk = 0.00
    else:
        dwell_risk = 0.00

    # -------------------------------------------------------------
    # Factor C: Fan-out / Fan-in Ratio & Smurfing Structure (Max weight: 0.25)
    # -------------------------------------------------------------
    # Detect one-to-many dispersal or many-to-one cash-out funneling
    in_deg = graph.in_degree(target_vpa)
    out_deg = graph.out_degree(target_vpa)

    fan_risk = 0.0
    # Smurfing fan-out: receives and immediately fans out to multiple receivers
    if out_deg >= 2 and in_deg >= 1 and created_hours < 48:
        fan_risk = 0.25
    elif out_deg >= 3:
        fan_risk = 0.20
    elif in_deg >= 3 and created_hours < 48:  # Funneling hub
        fan_risk = 0.20
    elif out_deg >= 1 and in_deg >= 1 and created_hours < 24:
        fan_risk = 0.15

    # -------------------------------------------------------------
    # Factor D: Connectivity to Known Mule Rings / Hubs (Max weight: 0.35)
    # -------------------------------------------------------------
    mule_nodes_in_neighborhood = [
        n for n in neighbor_nodes
        if graph.nodes[n].get("is_mule", False) or graph.nodes[n].get("flagged_history", 0) > 0
    ]
    mule_ratio = len(mule_nodes_in_neighborhood) / max(1, len(neighbor_nodes))

    connectivity_risk = 0.0
    # If target is explicitly flagged or directly linked to Hub / Mule L1/L2
    is_target_mule = target_data.get("is_mule", False)
    risk_tier = target_data.get("risk_tier", "CLEAN")

    if is_target_mule or risk_tier in ("MULE_L1", "MULE_L2", "HUB", "SUSPECT"):
        connectivity_risk += 0.25

    if flagged_history > 0:
        connectivity_risk += min(0.10, flagged_history * 0.03)

    if mule_ratio > 0.3:
        connectivity_risk += 0.10

    connectivity_risk = min(0.35, connectivity_risk)

    # -------------------------------------------------------------
    # Composite Score Aggregation (0.0 to 1.0)
    # -------------------------------------------------------------
    composite_score = age_risk + dwell_risk + fan_risk + connectivity_risk
    # Ensure realistic bounds
    composite_score = round(min(1.0, max(0.0, composite_score)), 3)

    is_mule_cluster = (composite_score >= 0.5) or is_target_mule or (risk_tier != "CLEAN" and risk_tier != "VICTIM")

    # Serialize cluster nodes and edges for frontend visualization
    cluster_nodes = list(neighbor_nodes)
    cluster_edges = []
    for u, v, data in subgraph.edges(data=True):
        cluster_edges.append({
            "source": u,
            "target": v,
            "amount": data.get("amount", 0.0),
            "dwell_time_sec": data.get("dwell_time_sec"),
            "tx_id": data.get("tx_id")
        })

    return {
        "graph_risk_score": composite_score,
        "is_mule_cluster": is_mule_cluster,
        "cluster_nodes": cluster_nodes,
        "cluster_edges": cluster_edges,
        "factors": {
            "account_age_penalty": age_risk,
            "dwell_time_risk": dwell_risk,
            "fan_ratio_risk": fan_risk,
            "mule_connectivity_risk": connectivity_risk,
            "target_created_hours_ago": created_hours,
            "flagged_history": flagged_history,
            "target_risk_tier": risk_tier
        }
    }
