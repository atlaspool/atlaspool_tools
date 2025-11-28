#!/usr/bin/env python3
"""
Block Update Monitor

Continuously monitors all pools and watches for when a new block is found.
This definitively shows which pools are on the real Bitcoin blockchain.

Usage:
    python3 monitor_block_updates.py [address] [pools_file]
"""

import socket
import json
import time
import threading
from typing import Dict, List, Optional, Tuple
from datetime import datetime


def load_pools(filename: str = 'pools.txt') -> List[Tuple[str, int, str]]:
    """
    Load pools from file
    Returns list of (host, port, name) tuples
    """
    pools = []
    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split()
                    if len(parts) >= 2:
                        host = parts[0]
                        port = int(parts[1])
                        name = f"{host}:{port}"
                        pools.append((host, port, name))
    except FileNotFoundError:
        print(f"Error: {filename} not found")
        return []
    
    return pools


def get_prevhash(host: str, port: int, address: str, timeout: int = 10) -> Dict:
    """
    Connect to a pool and get the first prevhash
    """
    result = {
        'host': host,
        'port': port,
        'prevhash': None,
        'job_id': None,
        'merkle_branches': None,
        'timestamp': None,
        'error': None,
        'authorized': False
    }
    
    sock = None
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        
        # Connect
        sock.connect((host, port))
        
        # Subscribe
        subscribe_msg = json.dumps({
            'id': 1,
            'method': 'mining.subscribe',
            'params': ['BlockMonitor/1.0', None, host, port]
        }) + '\n'
        sock.sendall(subscribe_msg.encode('utf-8'))
        
        # Authorize
        authorize_msg = json.dumps({
            'id': 2,
            'method': 'mining.authorize',
            'params': [address, 'x']
        }) + '\n'
        sock.sendall(authorize_msg.encode('utf-8'))
        
        # Read responses
        buffer = ""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                chunk = sock.recv(4096).decode('utf-8')
                if not chunk:
                    break
                    
                buffer += chunk
                
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        try:
                            data = json.loads(line)
                            
                            # Check for authorization response
                            if data.get('id') == 2:
                                result['authorized'] = data.get('result', False)
                            
                            # Check for mining.notify (job with prevhash)
                            if data.get('method') == 'mining.notify':
                                params = data.get('params', [])
                                if len(params) >= 9:
                                    result['prevhash'] = params[1]
                                    result['job_id'] = params[0]
                                    result['merkle_branches'] = len(params[4])
                                    result['timestamp'] = time.time()
                                    # Got what we need, exit
                                    sock.close()
                                    return result
                        
                        except json.JSONDecodeError:
                            pass
            
            except socket.timeout:
                break
        
        if result['prevhash'] is None:
            result['error'] = 'No job received'
    
    except socket.timeout:
        result['error'] = 'Connection timeout'
    except ConnectionRefusedError:
        result['error'] = 'Connection refused'
    except Exception as e:
        result['error'] = str(e)
    finally:
        if sock:
            try:
                sock.close()
            except:
                pass
    
    return result


def snapshot_all_pools(pools: List[Tuple[str, int, str]], address: str) -> Dict:
    """
    Connect to all pools simultaneously and capture prevhash
    """
    results = {}
    threads = []
    
    start_time = time.time()
    
    # Start all connections in parallel
    def worker(host, port, name):
        results[name] = get_prevhash(host, port, address)
    
    for host, port, name in pools:
        thread = threading.Thread(target=worker, args=(host, port, name))
        thread.start()
        threads.append(thread)
    
    # Wait for all to complete
    for thread in threads:
        thread.join()
    
    end_time = time.time()
    
    return results


def analyze_snapshot(results: Dict, snapshot_num: int, start_time: float):
    """
    Analyze a single snapshot
    """
    elapsed = time.time() - start_time
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    print(f"\n{'='*80}")
    print(f"SNAPSHOT #{snapshot_num} - {timestamp} (T+{elapsed:.0f}s)")
    print(f"{'='*80}")
    
    # Group by prevhash
    prevhash_groups = {}
    pools_with_prevhash = []
    pools_with_errors = []
    
    for name, result in results.items():
        if result['prevhash']:
            pools_with_prevhash.append(name)
            ph = result['prevhash'][:16]  # Use first 16 chars as key
            if ph not in prevhash_groups:
                prevhash_groups[ph] = {
                    'full_hash': result['prevhash'],
                    'pools': [],
                    'merkle_range': []
                }
            prevhash_groups[ph]['pools'].append(name)
            prevhash_groups[ph]['merkle_range'].append(result['merkle_branches'])
        elif result['error']:
            pools_with_errors.append((name, result['error']))
    
    print(f"\nPools responding: {len(pools_with_prevhash)}/{len(results)}")
    print(f"Unique prevhashes: {len(prevhash_groups)}")
    
    if len(prevhash_groups) == 1:
        print("✓ ALL POOLS ON SAME PREVHASH")
    else:
        print(f"⚠️  POOLS SPLIT ACROSS {len(prevhash_groups)} DIFFERENT PREVHASHES")
    
    # Display groups
    for i, (ph_short, data) in enumerate(prevhash_groups.items(), 1):
        merkle_min = min(data['merkle_range'])
        merkle_max = max(data['merkle_range'])
        print(f"\nGroup {i}: {ph_short}... ({len(data['pools'])} pools)")
        print(f"  Merkle branches: {merkle_min}-{merkle_max}")
        print(f"  Pools: {', '.join(sorted(data['pools']))}")
    
    # Show errors
    if pools_with_errors:
        print(f"\n⚠️  Pools with errors: {len(pools_with_errors)}")
        for name, error in pools_with_errors[:5]:  # Show first 5
            print(f"  {name}: {error}")
        if len(pools_with_errors) > 5:
            print(f"  ... and {len(pools_with_errors) - 5} more")
    
    return prevhash_groups


def detect_block_change(prev_groups: Dict, curr_groups: Dict) -> bool:
    """
    Detect if a new block was found
    """
    if not prev_groups or not curr_groups:
        return False
    
    prev_hashes = set(prev_groups.keys())
    curr_hashes = set(curr_groups.keys())
    
    # If any new prevhash appears, a block was found
    new_hashes = curr_hashes - prev_hashes
    
    return len(new_hashes) > 0


def monitor_pools(pools: List[Tuple[str, int, str]], address: str, max_snapshots: int = 100):
    """
    Continuously monitor pools until a block change is detected
    """
    print("="*80)
    print("BLOCK UPDATE MONITOR")
    print("="*80)
    print()
    print(f"Monitoring {len(pools)} pools")
    print(f"Address: {address}")
    print(f"Waiting for new block to be found...")
    print()
    print("This will take a snapshot every 30 seconds until a new block is found,")
    print("then show which pools updated and which didn't.")
    print()
    
    start_time = time.time()
    snapshot_num = 0
    prev_groups = None
    block_found = False
    
    while snapshot_num < max_snapshots:
        snapshot_num += 1
        
        # Take snapshot
        print(f"\nTaking snapshot #{snapshot_num}...")
        results = snapshot_all_pools(pools, address)
        curr_groups = analyze_snapshot(results, snapshot_num, start_time)
        
        # Check for block change
        if prev_groups and detect_block_change(prev_groups, curr_groups):
            print(f"\n{'='*80}")
            print("🎉 NEW BLOCK DETECTED!")
            print(f"{'='*80}")
            
            # Analyze which pools updated
            analyze_block_update(prev_groups, curr_groups, results)
            block_found = True
            break
        
        prev_groups = curr_groups
        
        # Wait before next snapshot
        if snapshot_num < max_snapshots:
            wait_time = 30
            print(f"\nWaiting {wait_time} seconds before next snapshot...")
            print("(Press Ctrl+C to stop)")
            try:
                time.sleep(wait_time)
            except KeyboardInterrupt:
                print("\n\nMonitoring stopped by user")
                break
    
    if not block_found:
        print(f"\n{'='*80}")
        print("MONITORING COMPLETE")
        print(f"{'='*80}")
        print(f"\nNo new block detected in {snapshot_num} snapshots")
        print("Bitcoin blocks are found approximately every 10 minutes on average.")
        print("You may need to wait longer or run the test again.")


def analyze_block_update(prev_groups: Dict, curr_groups: Dict, results: Dict):
    """
    Analyze which pools updated to the new block
    """
    print("\nAnalyzing pool responses to new block...\n")
    
    prev_hashes = set(prev_groups.keys())
    curr_hashes = set(curr_groups.keys())
    
    new_hashes = curr_hashes - prev_hashes
    old_hashes = prev_hashes - curr_hashes
    same_hashes = prev_hashes & curr_hashes
    
    print(f"New prevhash(es): {len(new_hashes)}")
    for ph in new_hashes:
        print(f"  {ph}... ({len(curr_groups[ph]['pools'])} pools)")
    
    print(f"\nOld prevhash(es) no longer seen: {len(old_hashes)}")
    for ph in old_hashes:
        print(f"  {ph}... (was {len(prev_groups[ph]['pools'])} pools)")
    
    print(f"\nPrevhash(es) still present: {len(same_hashes)}")
    for ph in same_hashes:
        print(f"  {ph}... ({len(curr_groups[ph]['pools'])} pools)")
    
    # Categorize pools
    updated_pools = []
    stuck_pools = []
    
    for name, result in results.items():
        if result['prevhash']:
            ph_short = result['prevhash'][:16]
            if ph_short in new_hashes:
                updated_pools.append(name)
            elif ph_short in same_hashes:
                stuck_pools.append(name)
    
    print(f"\n{'='*80}")
    print("POOL UPDATE ANALYSIS")
    print(f"{'='*80}")
    
    print(f"\n✓ UPDATED TO NEW BLOCK ({len(updated_pools)} pools):")
    for pool in sorted(updated_pools):
        print(f"  {pool}")
    
    if stuck_pools:
        print(f"\n✗ STUCK ON OLD BLOCK ({len(stuck_pools)} pools):")
        for pool in sorted(stuck_pools):
            print(f"  {pool}")
        
        print(f"\n{'='*80}")
        print("⚠️  WARNING: POOLS STUCK ON OLD BLOCK")
        print(f"{'='*80}")
        print("\nPools that don't update when a new block is found are either:")
        print("  1. Not connected to the real Bitcoin network")
        print("  2. Mining on a different chain (testnet/fork)")
        print("  3. Have severe infrastructure problems")
        print("  4. Are fake pools generating false jobs")
        print("\n⚠️  AVOID THESE POOLS - They may be scams!")


def main():
    import sys
    
    # Parse arguments
    address = '3Ax2uht6S5Lh6V5HLNhxfaHnEZU7KaFvSZ'  # Default
    pools_file = 'pools.txt'  # Default
    
    if len(sys.argv) > 1:
        address = sys.argv[1]
    if len(sys.argv) > 2:
        pools_file = sys.argv[2]
    
    # Load pools
    pools = load_pools(pools_file)
    
    if not pools:
        print(f"Error: No pools loaded from {pools_file}")
        print("\nExpected format (one per line):")
        print("  hostname port")
        print("\nExample:")
        print("  solo.ckpool.org 3333")
        print("  solo.atlaspool.io 3333")
        return
    
    print(f"Loaded {len(pools)} pools from {pools_file}")
    
    # Start monitoring
    monitor_pools(pools, address)


if __name__ == "__main__":
    main()
