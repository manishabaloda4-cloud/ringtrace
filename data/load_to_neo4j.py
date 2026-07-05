"""
RingTrace — Load synthetic accounts/transactions into Neo4j AuraDB.

Setup:
  1. Create a free AuraDB instance at https://neo4j.com/cloud/aura-free/
  2. Copy your connection URI, username, password into .env
  3. Run: python data/load_to_neo4j.py
"""

import csv
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()

URI = os.getenv("NEO4J_URI")
USER = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")


def clear_and_load_data(tx):
    tx.run("MATCH (n) DETACH DELETE n")

    with open("data/accounts.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tx.run("""
                CREATE (a:Account {
                    account_id: $account_id,
                    name: $name,
                    phone: $phone,
                    device_id: $device_id,
                    bank: $bank,
                    created_days_ago: toInteger($created_days_ago),
                    label: $label
                })
            """, **row)

    with open("data/transactions.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tx.run("""
                MATCH (src:Account {account_id: $src_account})
                MATCH (dst:Account {account_id: $dst_account})
                CREATE (src)-[:PAID {
                    txn_id: $txn_id,
                    amount: toFloat($amount),
                    timestamp: $timestamp
                }]->(dst)
            """, **row)


def create_constraint(tx):
    tx.run("CREATE CONSTRAINT IF NOT EXISTS FOR (a:Account) REQUIRE a.account_id IS UNIQUE")


def main():
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    with driver.session() as session:
        session.execute_write(create_constraint)
        session.execute_write(clear_and_load_data)
    driver.close()
    print("Loaded accounts + transactions into Neo4j AuraDB.")


if __name__ == "__main__":
    main()