"""
RingTrace — Fraud Detection Queries

Three real graph-based fraud detection patterns, each backed by a Cypher query:
  1. detect_cycles      -> cyclic money-laundering rings (A->B->C->D->A)
  2. detect_fanout       -> one account rapidly paying many new/dormant accounts
  3. detect_shared_device -> "different" accounts secretly linked by device/phone

These are the actual detection primitives real fraud teams use graph databases
for — this module is the technical core of the project, not just a demo layer.
"""

from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

URI = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")


def get_driver():
    return GraphDatabase.driver(URI, auth=(USER, PASSWORD))


CYPHER_CYCLES = """
MATCH path = (a:Account)-[:PAID*3..6]->(a)
WITH path, nodes(path) AS ns, relationships(path) AS rels
// Require chronological order — money must flow forward in time around the ring
WHERE ALL(i IN range(0, size(rels)-2)
          WHERE datetime(rels[i].timestamp) <= datetime(rels[i+1].timestamp))
  // Require the whole ring to close within 5 days — real laundering cycles are fast
  AND duration.inSeconds(datetime(rels[0].timestamp), datetime(rels[-1].timestamp)).seconds <= 5 * 86400
  // Require amounts to stay close hop-to-hop (allowing ~15% fee skim), not random noise
  AND ALL(i IN range(0, size(rels)-2)
          WHERE abs(rels[i].amount - rels[i+1].amount) <= 0.15 * rels[i].amount)
WITH path, [n IN nodes(path) | n.account_id] AS ring, size(rels) AS hops
RETURN DISTINCT ring, hops
ORDER BY hops
LIMIT 10
"""

CYPHER_FANOUT = """
MATCH (src:Account)-[p:PAID]->(dst:Account)
WHERE dst.created_days_ago <= 7
WITH src, collect(DISTINCT dst.account_id) AS targets, count(p) AS num_payments,
     collect(p.timestamp) AS times
WHERE num_payments >= 5
RETURN src.account_id AS source, targets, num_payments
ORDER BY num_payments DESC
LIMIT 10
"""

CYPHER_SHARED_DEVICE = """
MATCH (a:Account), (b:Account)
WHERE a.account_id < b.account_id
  AND (a.device_id = b.device_id OR a.phone = b.phone)
RETURN a.device_id AS device_id, a.phone AS phone,
       collect(DISTINCT a.account_id) + collect(DISTINCT b.account_id) AS linked_accounts
LIMIT 10
"""

CYPHER_ACCOUNT_CONTEXT = """
MATCH (a:Account {account_id: $account_id})
OPTIONAL MATCH (a)-[out:PAID]->(recipient)
OPTIONAL MATCH (sender)-[in:PAID]->(a)
RETURN a AS account,
       collect(DISTINCT {to: recipient.account_id, amount: out.amount}) AS sent,
       collect(DISTINCT {from: sender.account_id, amount: in.amount}) AS received
"""


def detect_cycles():
    with get_driver().session() as session:
        return [dict(r) for r in session.run(CYPHER_CYCLES)]


def detect_fanout():
    with get_driver().session() as session:
        return [dict(r) for r in session.run(CYPHER_FANOUT)]


def detect_shared_device():
    with get_driver().session() as session:
        results = [dict(r) for r in session.run(CYPHER_SHARED_DEVICE)]
        # dedupe accounts that only share a null/empty field artifact
        return [r for r in results if len(set(r["linked_accounts"])) >= 2]


def get_account_context(account_id):
    with get_driver().session() as session:
        result = session.run(CYPHER_ACCOUNT_CONTEXT, account_id=account_id)
        record = result.single()
        return dict(record) if record else None


def run_all_detections():
    return {
        "cycles": detect_cycles(),
        "fanout": detect_fanout(),
        "shared_device": detect_shared_device(),
    }
