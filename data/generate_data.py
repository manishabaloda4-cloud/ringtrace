"""
RingTrace — Synthetic UPI Transaction Data Generator
Creates a realistic-looking dataset of accounts + transactions with 3 planted
fraud patterns for demo purposes:
  1. Cyclic ring — money laundering loop (A -> B -> C -> D -> A)
  2. Fan-out mule — one source rapidly pays many new/dormant accounts
  3. Shared-device cluster — multiple "different" accounts share a device ID
     or phone number, indicating a single fraud operator controls them

Output: data/accounts.csv, data/transactions.csv
(Also directly loadable into Neo4j via load_to_neo4j.py)
"""

import csv
import random
from datetime import datetime, timedelta

random.seed(42)

NUM_LEGIT_ACCOUNTS = 120
OUTPUT_DIR = "data"

FIRST_NAMES = ["Amit", "Priya", "Rahul", "Sneha", "Vikram", "Anjali", "Rohan",
               "Kavya", "Suresh", "Neha", "Arjun", "Divya", "Karan", "Pooja",
               "Manish", "Ritu", "Sanjay", "Meera", "Ajay", "Shreya"]
LAST_NAMES = ["Sharma", "Verma", "Patel", "Gupta", "Reddy", "Iyer", "Singh",
              "Nair", "Joshi", "Rao", "Mehta", "Kulkarni", "Chauhan", "Bose"]
DEVICES = [f"DEV-{i:05d}" for i in range(1, 500)]  # large pool — legit accounts get unique devices
BANKS = ["SBI", "HDFC", "ICICI", "Axis", "PNB", "Kotak", "Paytm Bank"]

accounts = []
transactions = []
acc_id_counter = 1


def new_account(is_suspicious=False, shared_device=None, shared_phone=None, label="legit"):
    global acc_id_counter
    acc_id = f"ACC{acc_id_counter:04d}"
    name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
    device = shared_device if shared_device else f"DEV-{acc_id_counter:05d}"  # unique per account unless explicitly shared
    phone = shared_phone if shared_phone else f"9{random.randint(100000000, 999999999)}"
    acc_id_counter += 1
    bank = random.choice(BANKS)
    created_days_ago = random.randint(1, 5) if is_suspicious else random.randint(30, 1500)
    acc = {
        "account_id": acc_id,
        "name": name,
        "phone": phone,
        "device_id": device,
        "bank": bank,
        "created_days_ago": created_days_ago,
        "label": label,  # legit | fraud_ring | mule | operator (ground truth for demo/eval only)
    }
    accounts.append(acc)
    return acc


def add_txn(src, dst, amount, days_ago=None, explicit_ts=None):
    if explicit_ts is not None:
        ts = explicit_ts
    else:
        ts = datetime.now() - timedelta(days=days_ago, hours=random.randint(0, 23),
                                         minutes=random.randint(0, 59))
    transactions.append({
        "txn_id": f"TXN{len(transactions) + 1:06d}",
        "src_account": src,
        "dst_account": dst,
        "amount": amount,
        "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S"),
    })


# ---------- 1. Legit background accounts + normal transaction noise ----------
legit_accounts = [new_account() for _ in range(NUM_LEGIT_ACCOUNTS)]

for _ in range(400):
    src, dst = random.sample(legit_accounts, 2)
    add_txn(src["account_id"], dst["account_id"], round(random.uniform(50, 5000), 2),
            days_ago=random.randint(1, 180))


# ---------- 2. PLANTED PATTERN A: Cyclic laundering ring (4 accounts) ----------
ring_accounts = [new_account(is_suspicious=True, label="fraud_ring") for _ in range(4)]
ring_ids = [a["account_id"] for a in ring_accounts]
base_amount = 48000
ring_start_time = datetime.now() - timedelta(days=3)
for i in range(4):
    src = ring_ids[i]
    dst = ring_ids[(i + 1) % 4]
    # amount shrinks slightly each hop (fee skim) — realistic laundering signature
    amt = round(base_amount * (0.97 ** i), 2)
    # each hop happens 4-8 hours after the previous — strictly increasing, ring closes well within 5 days
    hop_time = ring_start_time + timedelta(hours=i * 6)
    add_txn(src, dst, amt, explicit_ts=hop_time)


# ---------- 3. PLANTED PATTERN B: Fan-out mule (one source, many new accounts) ----------
mule_source = new_account(is_suspicious=True, label="operator")
fanout_targets = [new_account(is_suspicious=True, label="mule") for _ in range(9)]
for t in fanout_targets:
    add_txn(mule_source["account_id"], t["account_id"],
            round(random.uniform(9500, 9999), 2),  # just under common reporting threshold
            days_ago=1)


# ---------- 4. PLANTED PATTERN C: Shared-device cluster (same device, "different" people) ----------
shared_device = "DEV-99999"
shared_phone = "9999999999"
cluster_accounts = [new_account(is_suspicious=True, shared_device=shared_device,
                                 shared_phone=shared_phone, label="fraud_ring")
                     for _ in range(5)]
# they pay each other in a tight loop too, then out to a legit-looking account
for i in range(len(cluster_accounts) - 1):
    add_txn(cluster_accounts[i]["account_id"], cluster_accounts[i + 1]["account_id"],
            round(random.uniform(15000, 20000), 2), days_ago=2 - i * 0.2)
cash_out_target = new_account(label="legit")
add_txn(cluster_accounts[-1]["account_id"], cash_out_target["account_id"],
        18000, days_ago=1.5)


# ---------- Write CSVs ----------
with open(f"{OUTPUT_DIR}/accounts.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["account_id", "name", "phone", "device_id",
                                            "bank", "created_days_ago", "label"])
    writer.writeheader()
    writer.writerows(accounts)

with open(f"{OUTPUT_DIR}/transactions.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["txn_id", "src_account", "dst_account",
                                            "amount", "timestamp"])
    writer.writeheader()
    writer.writerows(transactions)

print(f"Generated {len(accounts)} accounts and {len(transactions)} transactions.")
print(f"  - {NUM_LEGIT_ACCOUNTS} legit background accounts")
print(f"  - 1 cyclic laundering ring: {ring_ids}")
print(f"  - 1 fan-out mule cluster: source={mule_source['account_id']}, "
      f"targets={[t['account_id'] for t in fanout_targets]}")
print(f"  - 1 shared-device cluster: {[a['account_id'] for a in cluster_accounts]} "
      f"(device={shared_device}, phone={shared_phone})")
print("Files written to data/accounts.csv and data/transactions.csv")
