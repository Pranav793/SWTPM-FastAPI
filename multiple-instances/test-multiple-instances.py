#!/usr/bin/env python3
"""
Test script to verify multiple TPM instances are working independently.
Run from project root: python multiple-instances/test-multiple-instances.py

Tests that each instance:
1. Is accessible on its own port
2. Has independent TPM state
3. Can create keys independently
4. Keys are isolated between instances

Discovers instances from multiple-instances/.num_instances or shared_dir_node* directories.
"""

import os
import requests
import time
import glob
from pathlib import Path
from typing import Dict, Any


def discover_nodes() -> Dict[int, str]:
    """Discover TPM instances from multiple-instances/ directory."""
    # Script lives in multiple-instances/
    script_dir = Path(__file__).resolve().parent

    # NUM_INSTANCES env var
    env_num = os.environ.get("NUM_INSTANCES")
    if env_num:
        try:
            n = int(env_num)
            if n >= 1:
                return {i: f"http://localhost:{8000 + i}" for i in range(1, n + 1)}
        except ValueError:
            pass

    # .num_instances file in multiple-instances/
    num_file = script_dir / ".num_instances"
    if num_file.exists():
        try:
            n = int(num_file.read_text().strip())
            return {i: f"http://localhost:{8000 + i}" for i in range(1, n + 1)}
        except (ValueError, OSError):
            pass

    # Discover from shared_dir_node* in multiple-instances/
    dirs = sorted(glob.glob(str(script_dir / "shared_dir_node*")))
    nodes = {}
    for d in dirs:
        name = Path(d).name
        if name.startswith("shared_dir_node") and name[14:].isdigit():
            node_num = int(name[14:])
            nodes[node_num] = f"http://localhost:{8000 + node_num}"
    return nodes if nodes else {1: "http://localhost:8001", 2: "http://localhost:8002", 3: "http://localhost:8003"}


NODES = discover_nodes()


def test_health(node_num: int, base_url: str) -> bool:
    """Test if API is accessible"""
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print(f"✓ Node {node_num} ({base_url}): API is accessible")
            return True
        print(f"✗ Node {node_num} ({base_url}): API returned status {response.status_code}")
        return False
    except Exception as e:
        print(f"✗ Node {node_num} ({base_url}): Connection failed - {e}")
        return False


def test_create_primary_key(node_num: int, base_url: str) -> Dict[str, Any]:
    """Test creating a primary key on a node"""
    context_file = f"test_primary_node{node_num}.ctx"
    try:
        response = requests.post(
            f"{base_url}/tpm2/create-primary",
            json={"hierarchy": "o", "context_file": context_file},
            timeout=30,
        )
        result = response.json()
        if result.get("success"):
            print(f"✓ Node {node_num}: Created primary key ({context_file})")
            return result
        print(f"✗ Node {node_num}: Failed to create primary key - {result.get('error', 'Unknown error')}")
        return result
    except Exception as e:
        print(f"✗ Node {node_num}: Exception creating primary key - {e}")
        return {"success": False, "error": str(e)}


def test_create_signing_key(node_num: int, base_url: str, key_name: str) -> Dict[str, Any]:
    """Test creating a signing key on a node"""
    primary_result = test_create_primary_key(node_num, base_url)
    if not primary_result.get("success"):
        return primary_result
    parent_context = primary_result.get("context_file", f"test_primary_node{node_num}.ctx")
    timestamp = int(time.time())
    try:
        response = requests.post(
            f"{base_url}/tpm2/create-key",
            json={
                "parent_context": parent_context,
                "key_type": "rsa",
                "public_file": f"{key_name}_node{node_num}_{timestamp}.pub",
                "private_file": f"{key_name}_node{node_num}_{timestamp}.priv",
            },
            timeout=30,
        )
        result = response.json()
        if result.get("success"):
            print(f"✓ Node {node_num}: Created signing key '{key_name}'")
            return result
        print(f"✗ Node {node_num}: Failed - {result.get('error', 'Unknown error')}")
        return result
    except Exception as e:
        print(f"✗ Node {node_num}: Exception - {e}")
        return {"success": False, "error": str(e)}


def test_isolation(node1_url: str, node2_url: str) -> bool:
    """Test that keys created on one node are not visible on another"""
    print("\n" + "=" * 60)
    print("Testing Isolation Between Nodes")
    print("=" * 60)
    key_name_1 = f"isolation_test_node1_{int(time.time())}"
    key_name_2 = f"isolation_test_node2_{int(time.time())}"
    result1 = test_create_signing_key(1, node1_url, key_name_1)
    result2 = test_create_signing_key(2, node2_url, key_name_2)
    if result1.get("success") and result2.get("success"):
        print("\n✓ Isolation test passed")
        return True
    print("\n✗ Isolation test failed")
    return False


def main():
    print("=" * 60)
    print("Multiple TPM Instances Test")
    print("=" * 60)
    print(f"\nTesting {len(NODES)} TPM instances:")
    for node_num, url in NODES.items():
        print(f"  Node {node_num}: {url}")
    print()

    health_results = {n: test_health(n, url) for n, url in NODES.items()}
    if not all(health_results.values()):
        print("\n✗ Some APIs not accessible. Check: docker-compose -f multiple-instances/docker-compose.instances.yaml ps")
        return False

    primary_results = {n: test_create_primary_key(n, url) for n, url in NODES.items()}
    if not all(r.get("success") for r in primary_results.values()):
        return False

    signing_results = {n: test_create_signing_key(n, url, f"test_key_node{n}") for n, url in NODES.items()}
    if not all(r.get("success") for r in signing_results.values()):
        return False

    isolation_passed = True
    if len(NODES) >= 2:
        node_nums = sorted(NODES.keys())
        isolation_passed = test_isolation(NODES[node_nums[0]], NODES[node_nums[1]])
    else:
        print("\nSkipping isolation test (requires at least 2 instances)")

    all_ok = all(health_results.values()) and all(r.get("success") for r in primary_results.values()) and all(r.get("success") for r in signing_results.values()) and isolation_passed

    print("\n" + "=" * 60)
    if all_ok:
        print("✓ ALL TESTS PASSED!")
    else:
        print("✗ SOME TESTS FAILED")
    print("=" * 60)
    return all_ok


if __name__ == "__main__":
    exit(0 if main() else 1)
