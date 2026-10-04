import os
import csv
import time
import random
from typing import Dict, Any, List, Tuple
import networkx as nx

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
SAMPLE_CSV_PATH = os.path.join(DATA_DIR, "sample_transactions.csv")
UPI_CSV_PATH = os.path.join(DATA_DIR, "upi_transactions.csv")
DATASET_CSV_PATH = SAMPLE_CSV_PATH if os.path.exists(SAMPLE_CSV_PATH) else UPI_CSV_PATH


def ensure_dataset_csv_exists(force_regenerate: bool = False):
    """
    Generates a realistic transaction dataset CSV if it does not already exist.
    Contains both benign merchant/P2P clusters and active multi-hop mule dispersal rings.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    if not force_regenerate and os.path.exists(SAMPLE_CSV_PATH) and os.path.getsize(SAMPLE_CSV_PATH) > 1000:
        return
    if not force_regenerate and os.path.exists(UPI_CSV_PATH) and os.path.getsize(UPI_CSV_PATH) > 1000:
        return



    now_ts = int(time.time())
    headers = [
        "tx_id", "step", "timestamp_sec", "source_vpa", "target_vpa",
        "amount", "tx_type", "dwell_time_sec", "is_fraud", "is_flagged_fraud",
        "source_balance_before", "source_balance_after",
        "target_balance_before", "target_balance_after",
        "source_account_age_hours", "target_account_age_hours"
    ]

    rows = []
    tx_counter = 1000

    # 1. Clean Merchants & Regular Users (45 accounts)
    merchants = [f"merchant_{i:02d}@{bank}" for i, bank in enumerate([
        "okhdfcbank", "okicici", "okaxis", "oksbi", "paytm",
        "okhdfcbank", "okicici", "okaxis", "oksbi", "paytm",
        "okhdfcbank", "okicici", "okaxis", "oksbi", "paytm"
    ], start=1)]

    clean_users = [
        f"user_{i:02d}@{random.choice(['okhdfcbank', 'okaxis', 'oksbi', 'okicici', 'paytm'])}"
        for i in range(1, 31)
    ]

    # Ensure every merchant receives at least one transaction
    for idx, m in enumerate(merchants):
        u = clean_users[idx % len(clean_users)]
        u_age = round(random.uniform(720, 8760), 1)
        tx_counter += 1
        amt = round(random.uniform(150.0, 4800.0), 2)
        dwell = round(random.uniform(3600, 86400 * 3), 1)
        ts = now_ts - random.randint(1800, 86400 * 5)
        rows.append([
            f"TXN_{tx_counter}", random.randint(1, 100), ts, u, m,
            amt, "MERCHANT_PAYMENT", dwell, 0, 0,
            50000.0, 50000.0 - amt, 120000.0, 120000.0 + amt,
            u_age, round(random.uniform(1400, 9000), 1)
        ])

    # Clean P2P and Additional Merchant Transactions
    for u in clean_users:
        u_age = round(random.uniform(720, 8760), 1)
        # Transactions to 1-2 merchants
        for m in random.sample(merchants, k=random.randint(1, 2)):
            tx_counter += 1
            amt = round(random.uniform(150.0, 4800.0), 2)
            dwell = round(random.uniform(3600, 86400 * 3), 1)
            ts = now_ts - random.randint(1800, 86400 * 5)
            rows.append([
                f"TXN_{tx_counter}", random.randint(1, 100), ts, u, m,
                amt, "MERCHANT_PAYMENT", dwell, 0, 0,
                50000.0, 50000.0 - amt, 120000.0, 120000.0 + amt,
                u_age, round(random.uniform(1400, 9000), 1)
            ])

        # Transactions to 1 peer
        peer = random.choice([p for p in clean_users if p != u])
        tx_counter += 1
        amt = round(random.uniform(300.0, 5000.0), 2)
        dwell = round(random.uniform(7200, 86400 * 7), 1)
        ts = now_ts - random.randint(1800, 86400 * 4)
        rows.append([
            f"TXN_{tx_counter}", random.randint(1, 100), ts, u, peer,
            amt, "P2P_TRANSFER", dwell, 0, 0,
            45000.0, 45000.0 - amt, 25000.0, 25000.0 + amt,
            u_age, round(random.uniform(720, 8760), 1)
        ])

    # 2. Mule Dispersal Ring (15 accounts: 1 Victim -> 3 L1 Mules -> 6 L2 Mules -> 1 Hub + 4 Smurfs)
    victim = "victim_01@upi"
    mules_l1 = [f"mule_L1_{i:02d}@upi" for i in range(1, 4)]
    mules_l2 = [f"mule_L2_{i:02d}@upi" for i in range(1, 7)]
    cashout_hub = "aggregator_hub_01@upi"
    mules_smurf = [f"mule_smurf_{i:02d}@upi" for i in range(1, 5)]

    # Step A: Victim -> Layer-1 Mules
    for l1 in mules_l1:
        tx_counter += 1
        amt = round(random.uniform(25000.0, 35000.0), 2)
        dwell = random.randint(20, 85)
        ts = now_ts - 240
        rows.append([
            f"TXN_SCAM_{tx_counter}", 1, ts, victim, l1,
            amt, "DISPERSAL_L1", dwell, 1, 1,
            95000.0, 95000.0 - amt, 0.0, amt,
            2400.0, round(random.uniform(4.0, 18.0), 1)
        ])

    # Step B: Layer-1 Mules -> Layer-2 Mules
    for i, l1 in enumerate(mules_l1):
        target_pair = mules_l2[i * 2 : (i + 1) * 2]
        for l2 in target_pair:
            tx_counter += 1
            amt = round(random.uniform(11500.0, 14500.0), 2)
            dwell = random.randint(35, 110)
            ts = now_ts - 150
            rows.append([
                f"TXN_MULE_{tx_counter}", 2, ts, l1, l2,
                amt, "DISPERSAL_L2", dwell, 1, 1,
                25000.0, 25000.0 - amt, 500.0, 500.0 + amt,
                round(random.uniform(4.0, 18.0), 1), round(random.uniform(2.0, 12.0), 1)
            ])

    # Smurfing buffer transactions
    for i, smurf in enumerate(mules_smurf):
        src_l1 = mules_l1[i % len(mules_l1)]
        dst_l2 = mules_l2[(i + 1) % len(mules_l2)]
        tx_counter += 1
        amt_a = round(random.uniform(2500.0, 4800.0), 2)
        dwell_a = random.randint(30, 90)
        rows.append([
            f"TXN_SMURF_A_{tx_counter}", 2, now_ts - 120, src_l1, smurf,
            amt_a, "SMURF_BUFFER", dwell_a, 1, 1,
            15000.0, 15000.0 - amt_a, 100.0, 100.0 + amt_a,
            12.0, round(random.uniform(6.0, 20.0), 1)
        ])
        tx_counter += 1
        amt_b = round(amt_a - random.uniform(50, 150), 2)
        dwell_b = random.randint(25, 75)
        rows.append([
            f"TXN_SMURF_B_{tx_counter}", 3, now_ts - 70, smurf, dst_l2,
            amt_b, "SMURF_BUFFER", dwell_b, 1, 1,
            amt_a, amt_a - amt_b, 12000.0, 12000.0 + amt_b,
            round(random.uniform(6.0, 20.0), 1), round(random.uniform(2.0, 12.0), 1)
        ])

    # Step C: Layer-2 Mules -> Cash-out Hub
    for l2 in mules_l2:
        tx_counter += 1
        amt = round(random.uniform(11000.0, 14200.0), 2)
        dwell = random.randint(25, 75)
        ts = now_ts - 30
        rows.append([
            f"TXN_CASHOUT_{tx_counter}", 4, ts, l2, cashout_hub,
            amt, "CASHOUT_HUB", dwell, 1, 1,
            14000.0, 14000.0 - amt, 45000.0, 45000.0 + amt,
            round(random.uniform(2.0, 12.0), 1), 14.0
        ])

    with open(DATASET_CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)


class DatasetGraphPipeline:
    """
    Pipeline that ingests the transaction CSV datasheet, computes topological & behavioral
    features for each account node, and builds a queryable NetworkX directed graph.
    """
    def __init__(self, csv_path: str = DATASET_CSV_PATH):
        self.csv_path = csv_path
        self.graph: nx.DiGraph = nx.DiGraph()
        self.node_stats: Dict[str, Dict[str, Any]] = {}
        self.load_and_build_graph()

    def load_and_build_graph(self) -> nx.DiGraph:
        ensure_dataset_csv_exists()
        G = nx.DiGraph()
        node_records: Dict[str, Dict[str, Any]] = {}

        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                src = row["source_vpa"].strip()
                tgt = row["target_vpa"].strip()
                amt = float(row["amount"])
                dwell = float(row.get("dwell_time_sec", 3600.0))
                is_fraud = int(row.get("is_fraud", 0)) == 1
                tx_id = row.get("tx_id", "")
                tx_type = row.get("tx_type", "P2P")
                src_age = float(row.get("source_account_age_hours", 1000.0))
                tgt_age = float(row.get("target_account_age_hours", 1000.0))

                # Track source node
                if src not in node_records:
                    node_records[src] = {
                        "account_age_hours": src_age,
                        "flagged_history": 1 if is_fraud else 0,
                        "is_mule": is_fraud and "mule" in src.lower(),
                        "dwell_times": [],
                        "sent_amts": [],
                        "recv_amts": []
                    }
                node_records[src]["sent_amts"].append(amt)
                node_records[src]["dwell_times"].append(dwell)
                if is_fraud:
                    node_records[src]["flagged_history"] += 1

                # Track target node
                if tgt not in node_records:
                    node_records[tgt] = {
                        "account_age_hours": tgt_age,
                        "flagged_history": 1 if is_fraud else 0,
                        "is_mule": is_fraud and ("mule" in tgt.lower() or "hub" in tgt.lower()),
                        "dwell_times": [],
                        "sent_amts": [],
                        "recv_amts": []
                    }
                node_records[tgt]["recv_amts"].append(amt)
                node_records[tgt]["dwell_times"].append(dwell)
                if is_fraud:
                    node_records[tgt]["flagged_history"] += 1

                # Add directed transaction edge
                G.add_edge(
                    src, tgt,
                    tx_id=tx_id,
                    amount=amt,
                    dwell_time_sec=dwell,
                    tx_type=tx_type,
                    is_fraud=is_fraud
                )

        # Compute aggregate node features
        for node_id, meta in node_records.items():
            in_deg = G.in_degree(node_id) if G.has_node(node_id) else 0
            out_deg = G.out_degree(node_id) if G.has_node(node_id) else 0
            dwells = meta["dwell_times"]
            avg_dwell = sum(dwells) / max(1, len(dwells)) if dwells else 3600.0
            min_dwell = min(dwells) if dwells else 3600.0

            # Determine risk tier
            if node_id.startswith("victim"):
                risk_tier = "VICTIM"
                is_mule = False
            elif "hub" in node_id:
                risk_tier = "HUB"
                is_mule = True
            elif "mule_L1" in node_id:
                risk_tier = "MULE_L1"
                is_mule = True
            elif "mule_L2" in node_id:
                risk_tier = "MULE_L2"
                is_mule = True
            elif "smurf" in node_id:
                risk_tier = "SUSPECT"
                is_mule = True
            elif node_id.startswith("merchant"):
                risk_tier = "CLEAN"
                is_mule = False
            else:
                risk_tier = "CLEAN"
                is_mule = False

            G.add_node(
                node_id,
                label=node_id.split("@")[0],
                risk_tier=risk_tier,
                account_age_hours=meta["account_age_hours"],
                created_hours_ago=meta["account_age_hours"],
                flagged_history=meta["flagged_history"],
                is_mule=is_mule,
                in_degree=in_deg,
                out_degree=out_deg,
                avg_dwell_sec=round(avg_dwell, 1),
                min_dwell_sec=round(min_dwell, 1)
            )

        self.graph = G
        self.node_stats = node_records
        return G


# Global singleton instance
PIPELINE_INSTANCE = DatasetGraphPipeline()


def get_dataset_transactions() -> List[Dict[str, Any]]:
    """Reads and parses transactions from the active dataset CSV."""
    ensure_dataset_csv_exists()
    transactions = []
    if not os.path.exists(DATASET_CSV_PATH):
        return transactions
    with open(DATASET_CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                transactions.append({
                    "tx_id": row.get("tx_id", ""),
                    "step": int(row.get("step", 1)),
                    "timestamp_sec": int(float(row.get("timestamp_sec", time.time()))),
                    "source_vpa": row.get("source_vpa", "").strip(),
                    "target_vpa": row.get("target_vpa", "").strip(),
                    "amount": float(row.get("amount", 0.0)),
                    "tx_type": row.get("tx_type", "P2P"),
                    "dwell_time_sec": float(row.get("dwell_time_sec", 3600.0)),
                    "is_fraud": int(row.get("is_fraud", 0)) == 1,
                    "is_flagged_fraud": int(row.get("is_flagged_fraud", 0)) == 1,
                    "source_balance_before": float(row.get("source_balance_before", 0.0)),
                    "source_balance_after": float(row.get("source_balance_after", 0.0)),
                    "target_balance_before": float(row.get("target_balance_before", 0.0)),
                    "target_balance_after": float(row.get("target_balance_after", 0.0)),
                    "source_account_age_hours": float(row.get("source_account_age_hours", 1000.0)),
                    "target_account_age_hours": float(row.get("target_account_age_hours", 1000.0))
                })
            except Exception:
                continue
    return transactions


def get_pipeline() -> DatasetGraphPipeline:
    global PIPELINE_INSTANCE
    return PIPELINE_INSTANCE


def get_dataset_graph() -> nx.DiGraph:
    return get_pipeline().graph


def reset_dataset_pipeline(force_regenerate: bool = True) -> nx.DiGraph:
    global PIPELINE_INSTANCE
    ensure_dataset_csv_exists(force_regenerate=force_regenerate)
    PIPELINE_INSTANCE = DatasetGraphPipeline()
    return PIPELINE_INSTANCE.graph


