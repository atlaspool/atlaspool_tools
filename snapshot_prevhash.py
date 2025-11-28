#!/usr/bin/env python3
"""
Simultaneous Prevhash Snapshot

Connects to multiple pools at the same time and captures their prevhash
to verify if they're all mining on the same blockchain tip.
"""

import socket
import json
import time
import threading
from typing import Dict, Optional


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
            'params': ['PrevhashSnapshot/1.0', None, host, port]
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


def snapshot_all_pools(address: str) -> Dict:
    """
    Connect to all pools simultaneously and capture prevhash
    """
    pools = [
        ('solo.atlaspool.io', 3333, 'AtlasPool'),
        ('solo.ckpool.org', 3333, 'CKPool'),
        ('public-pool.io', 21496, 'Public Pool'),
        ('104.168.100.92', 7112, 'LuckyMonster US'),
        ('45.95.172.24', 7112, 'LuckyMonster EU'),
        ('92.119.126.14', 6057, 'zsolo.bid'),
    ]
    
    results = {}
    threads = []
    
    print("Connecting to all pools simultaneously...")
    print(f"Using address: {address}")
    print()
    
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
    
    print(f"All connections completed in {end_time - start_time:.2f} seconds")
    print()
    
    return results


def analyze_results(results: Dict):
    """
    Analyze and display the prevhash snapshot
    """
    print("="*80)
    print("PREVHASH SNAPSHOT RESULTS")
    print("="*80)
    print()
    
    # Display individual results
    for name, result in results.items():
        print(f"{name} ({result['host']}:{result['port']}):")
        
        if result['error']:
            print(f"  ✗ Error: {result['error']}")
        else:
            print(f"  ✓ Authorized: {result['authorized']}")
            if result['prevhash']:
                print(f"  Prevhash: {result['prevhash'][:32]}...")
                print(f"  Job ID: {result['job_id']}")
                print(f"  Merkle branches: {result['merkle_branches']}")
                print(f"  Timestamp: {result['timestamp']:.3f}")
            else:
                print(f"  ⚠️  No prevhash received")
        print()
    
    # Analyze prevhash distribution
    print("="*80)
    print("PREVHASH ANALYSIS")
    print("="*80)
    print()
    
    prevhash_groups = {}
    pools_with_prevhash = []
    
    for name, result in results.items():
        if result['prevhash']:
            pools_with_prevhash.append(name)
            ph = result['prevhash']
            if ph not in prevhash_groups:
                prevhash_groups[ph] = []
            prevhash_groups[ph].append(name)
    
    if not prevhash_groups:
        print("⚠️  No pools returned prevhash data")
        return
    
    print(f"Total pools with prevhash: {len(pools_with_prevhash)}")
    print(f"Unique prevhashes: {len(prevhash_groups)}")
    print()
    
    if len(prevhash_groups) == 1:
        print("✓ ALL POOLS HAVE THE SAME PREVHASH")
        print("  This is expected - they're all mining on the same blockchain")
        prevhash = list(prevhash_groups.keys())[0]
        print(f"  Prevhash: {prevhash[:32]}...")
        print(f"  Pools: {', '.join(prevhash_groups[prevhash])}")
    else:
        print("⚠️  POOLS HAVE DIFFERENT PREVHASHES")
        print("  This could mean:")
        print("    1. A new block was found during the test (timing issue)")
        print("    2. Some pools are slow to update")
        print("    3. Some pools are on a different chain (very unlikely)")
        print()
        
        for i, (prevhash, pool_list) in enumerate(prevhash_groups.items(), 1):
            print(f"Group {i}: {prevhash[:32]}...")
            print(f"  Pools: {', '.join(pool_list)}")
            print()
    
    # Time spread analysis
    print("="*80)
    print("TIMING ANALYSIS")
    print("="*80)
    print()
    
    timestamps = [(name, r['timestamp']) for name, r in results.items() if r['timestamp']]
    if timestamps:
        timestamps.sort(key=lambda x: x[1])
        first_time = timestamps[0][1]
        
        print("Order of responses:")
        for name, ts in timestamps:
            delta = (ts - first_time) * 1000  # Convert to ms
            print(f"  {name}: +{delta:.0f}ms")
        
        total_spread = (timestamps[-1][1] - timestamps[0][1]) * 1000
        print()
        print(f"Total time spread: {total_spread:.0f}ms")
        
        if total_spread < 1000:
            print("✓ All responses within 1 second - good snapshot")
        else:
            print("⚠️  Responses spread over >1 second - may have timing issues")


def main():
    import sys
    
    print("="*80)
    print("SIMULTANEOUS PREVHASH SNAPSHOT")
    print("="*80)
    print()
    print("This tool connects to all pools at the same time and captures")
    print("their prevhash to verify if they're mining on the same blockchain.")
    print()
    
    # Use a valid address for legitimate pools, invalid for scam pools
    if len(sys.argv) > 1:
        address = sys.argv[1]
    else:
        # Use a valid-looking address that will work with legitimate pools
        address = '3Ax2uht6S5Lh6V5HLNhxfaHnEZU7KaFvSZ'
    
    results = snapshot_all_pools(address)
    analyze_results(results)
    
    print()
    print("="*80)
    print("CONCLUSION")
    print("="*80)
    print()
    print("Expected behavior:")
    print("  • All pools should have the same prevhash (same blockchain)")
    print("  • Timing spread should be minimal (< 1 second)")
    print()
    print("If pools have different prevhashes:")
    print("  • Most likely: A new block was found during the test")
    print("  • Check timing spread - if >10 seconds, this is likely")
    print("  • Run the test again to confirm")
    print()


if __name__ == "__main__":
    main()
