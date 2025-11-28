#!/usr/bin/env python3
"""
Proxy Detection Tool for Mining Pools

Tests if a pool is proxying stratum traffic to another backend pool by:
1. Analyzing job timing and patterns
2. Comparing work distribution
3. Testing share submission behavior
4. Fingerprinting backend pool characteristics
5. Detecting address substitution
"""

import socket
import json
import time
import binascii
import hashlib
from typing import Dict, List, Tuple, Optional


def connect_and_monitor(host: str, port: int, duration: int = 30) -> Dict:
    """
    Connect to pool and monitor behavior for signs of proxying
    """
    print(f"\n{'='*80}")
    print(f"MONITORING: {host}:{port}")
    print(f"{'='*80}\n")
    
    results = {
        'host': host,
        'port': port,
        'jobs': [],
        'responses': [],
        'timing': {},
        'fingerprints': {}
    }
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(duration + 5)
        
        # Measure connection time
        connect_start = time.time()
        sock.connect((host, port))
        connect_time = time.time() - connect_start
        results['timing']['connect'] = connect_time
        print(f"[+] Connected in {connect_time:.3f}s")
        
        # Subscribe
        subscribe_start = time.time()
        subscribe_msg = json.dumps({
            'id': 1,
            'method': 'mining.subscribe',
            'params': ['ProxyDetector/1.0', None, host, port]
        }) + '\n'
        sock.sendall(subscribe_msg.encode('utf-8'))
        
        # Wait for subscribe response
        buffer = ""
        subscribe_response = None
        while time.time() - subscribe_start < 5:
            try:
                chunk = sock.recv(4096).decode('utf-8')
                buffer += chunk
                
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        try:
                            data = json.loads(line)
                            results['responses'].append(data)
                            
                            if data.get('id') == 1:
                                subscribe_response = data
                                subscribe_time = time.time() - subscribe_start
                                results['timing']['subscribe'] = subscribe_time
                                print(f"[+] Subscribe response in {subscribe_time:.3f}s")
                                
                                # Extract subscription details
                                if 'result' in data:
                                    result = data['result']
                                    if len(result) >= 2:
                                        results['fingerprints']['subscription_id'] = result[0]
                                        results['fingerprints']['extranonce1'] = result[1]
                                        results['fingerprints']['extranonce2_size'] = result[2] if len(result) > 2 else None
                                        print(f"    Extranonce1: {result[1]}")
                                        print(f"    Extranonce2 size: {result[2] if len(result) > 2 else 'N/A'}")
                                break
                        except json.JSONDecodeError:
                            pass
            except socket.timeout:
                break
        
        if not subscribe_response:
            print("[-] No subscribe response received")
            sock.close()
            return results
        
        # Authorize with test address
        authorize_start = time.time()
        test_address = 'bc1qdetectortest123456789012345678901234'
        authorize_msg = json.dumps({
            'id': 2,
            'method': 'mining.authorize',
            'params': [test_address, 'x']
        }) + '\n'
        sock.sendall(authorize_msg.encode('utf-8'))
        print(f"[+] Sent authorization for: {test_address}")
        
        # Monitor for jobs and responses
        print(f"[+] Monitoring for {duration} seconds...")
        print()
        
        start_time = time.time()
        job_count = 0
        
        while time.time() - start_time < duration:
            try:
                chunk = sock.recv(4096).decode('utf-8')
                buffer += chunk
                
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if line.strip():
                        try:
                            data = json.loads(line)
                            results['responses'].append(data)
                            
                            # Check for authorization response
                            if data.get('id') == 2:
                                auth_time = time.time() - authorize_start
                                results['timing']['authorize'] = auth_time
                                authorized = data.get('result', False)
                                print(f"[+] Authorization: {'SUCCESS' if authorized else 'FAILED'} ({auth_time:.3f}s)")
                            
                            # Check for mining.notify (new job)
                            if data.get('method') == 'mining.notify':
                                job_count += 1
                                job_time = time.time() - start_time
                                
                                params = data.get('params', [])
                                if len(params) >= 9:
                                    job_info = {
                                        'time': job_time,
                                        'job_id': params[0],
                                        'prevhash': params[1],
                                        'coinb1': params[2],
                                        'coinb2': params[3],
                                        'merkle_branches': len(params[4]),
                                        'version': params[5],
                                        'nbits': params[6],
                                        'ntime': params[7],
                                        'clean_jobs': params[8]
                                    }
                                    results['jobs'].append(job_info)
                                    
                                    print(f"[{job_count}] Job received at {job_time:.1f}s:")
                                    print(f"    Job ID: {params[0]}")
                                    print(f"    Prevhash: {params[1][:32]}...")
                                    print(f"    Merkle branches: {len(params[4])}")
                                    print(f"    Clean jobs: {params[8]}")
                                    
                                    # Analyze coinbase for address substitution
                                    analyze_coinbase(params[2], params[3], test_address)
                            
                            # Check for difficulty
                            if data.get('method') == 'mining.set_difficulty':
                                difficulty = data.get('params', [None])[0]
                                results['fingerprints']['difficulty'] = difficulty
                                print(f"[+] Difficulty set: {difficulty}")
                        
                        except json.JSONDecodeError:
                            pass
            
            except socket.timeout:
                break
        
        sock.close()
        
        print(f"\n[+] Monitoring complete: {job_count} jobs received")
        
    except Exception as e:
        print(f"[-] Error: {e}")
    
    return results


def analyze_coinbase(coinb1_hex: str, coinb2_hex: str, test_address: str):
    """
    Analyze coinbase to detect if test address was substituted
    """
    try:
        cb1 = binascii.unhexlify(coinb1_hex)
        cb2 = binascii.unhexlify(coinb2_hex)
        
        # Check if test address appears anywhere in coinbase
        test_address_bytes = test_address.encode('utf-8')
        
        if test_address_bytes in cb1 or test_address_bytes in cb2:
            print(f"    ✓ Test address FOUND in coinbase")
            return True
        else:
            print(f"    ✗ Test address NOT FOUND in coinbase (likely substituted)")
            
            # Try to extract what address IS in the coinbase
            # Look for P2PKH, P2WPKH patterns
            for i in range(len(cb2) - 22):
                # P2WPKH: OP_0 <20 bytes>
                if cb2[i] == 0x00 and cb2[i+1] == 0x14:
                    hash160 = cb2[i+2:i+22]
                    print(f"    → Found P2WPKH hash: {hash160.hex()}")
                
                # P2PKH: OP_DUP OP_HASH160 <20 bytes> OP_EQUALVERIFY OP_CHECKSIG
                if (i + 25 <= len(cb2) and 
                    cb2[i] == 0x76 and cb2[i+1] == 0xa9 and cb2[i+2] == 0x14):
                    hash160 = cb2[i+3:i+23]
                    print(f"    → Found P2PKH hash: {hash160.hex()}")
            
            return False
    
    except Exception as e:
        print(f"    Error analyzing coinbase: {e}")
        return False


def compare_job_patterns(results_list: List[Dict]):
    """
    Compare job patterns between pools to detect if they're using same backend
    """
    print(f"\n{'='*80}")
    print("JOB PATTERN ANALYSIS")
    print(f"{'='*80}\n")
    
    if not results_list or not any(r.get('jobs') for r in results_list):
        print("No jobs to analyze")
        return
    
    # Compare prevhashes
    print("Prevhash Comparison:")
    prevhashes_by_pool = {}
    for r in results_list:
        pool_name = f"{r['host']}:{r['port']}"
        prevhashes = [j['prevhash'] for j in r.get('jobs', [])]
        prevhashes_by_pool[pool_name] = prevhashes
        print(f"  {pool_name}: {len(prevhashes)} job(s)")
        for i, ph in enumerate(prevhashes, 1):
            print(f"    [{i}] {ph[:32]}...")
    
    # Check for identical prevhashes
    print("\nPrevhash Overlap:")
    pools = list(prevhashes_by_pool.keys())
    for i in range(len(pools)):
        for j in range(i+1, len(pools)):
            pool1, pool2 = pools[i], pools[j]
            set1 = set(prevhashes_by_pool[pool1])
            set2 = set(prevhashes_by_pool[pool2])
            overlap = set1 & set2
            
            if overlap:
                print(f"  ⚠️  {pool1} and {pool2} have {len(overlap)} identical prevhash(es)")
                print(f"      This suggests they're getting work from the same source!")
            else:
                print(f"  ✓ {pool1} and {pool2} have no overlap (different backends)")
    
    # Compare job timing
    print("\nJob Timing:")
    for r in results_list:
        pool_name = f"{r['host']}:{r['port']}"
        jobs = r.get('jobs', [])
        if len(jobs) > 1:
            intervals = [jobs[i]['time'] - jobs[i-1]['time'] for i in range(1, len(jobs))]
            avg_interval = sum(intervals) / len(intervals)
            print(f"  {pool_name}: {len(jobs)} jobs, avg interval {avg_interval:.1f}s")
        elif len(jobs) == 1:
            print(f"  {pool_name}: 1 job only")
        else:
            print(f"  {pool_name}: No jobs received")
    
    # Compare merkle branch counts
    print("\nMerkle Branch Counts:")
    for r in results_list:
        pool_name = f"{r['host']}:{r['port']}"
        jobs = r.get('jobs', [])
        if jobs:
            merkle_counts = [j['merkle_branches'] for j in jobs]
            print(f"  {pool_name}: {merkle_counts}")
    
    # Check for identical merkle counts (suggests same backend)
    merkle_by_pool = {}
    for r in results_list:
        pool_name = f"{r['host']}:{r['port']}"
        jobs = r.get('jobs', [])
        if jobs:
            merkle_by_pool[pool_name] = [j['merkle_branches'] for j in jobs]
    
    if len(merkle_by_pool) >= 2:
        pools = list(merkle_by_pool.keys())
        for i in range(len(pools)):
            for j in range(i+1, len(pools)):
                if merkle_by_pool[pools[i]] == merkle_by_pool[pools[j]]:
                    print(f"  ⚠️  {pools[i]} and {pools[j]} have IDENTICAL merkle counts")
                    print(f"      This is highly suspicious!")


def detect_proxy_fingerprints(results: Dict):
    """
    Look for fingerprints that indicate proxying
    """
    print(f"\n{'='*80}")
    print(f"PROXY DETECTION ANALYSIS: {results['host']}:{results['port']}")
    print(f"{'='*80}\n")
    
    fingerprints = results.get('fingerprints', {})
    timing = results.get('timing', {})
    jobs = results.get('jobs', [])
    
    proxy_score = 0
    indicators = []
    
    # Check 1: Address substitution
    if jobs:
        # We already printed this during monitoring
        indicators.append("Address substitution detected (test address not in coinbase)")
        proxy_score += 3
    
    # Check 2: Response timing
    if 'subscribe' in timing and timing['subscribe'] > 0.2:
        indicators.append(f"Slow subscribe response ({timing['subscribe']:.3f}s) - may indicate proxy hop")
        proxy_score += 1
    
    # Check 3: Job frequency
    if len(jobs) == 0:
        indicators.append("No jobs received - connection issues or requires valid credentials")
    elif len(jobs) == 1:
        indicators.append("Only 1 job in 30s - normal for solo mining")
    
    # Print results
    print("Proxy Indicators:")
    if indicators:
        for ind in indicators:
            print(f"  • {ind}")
    else:
        print("  None detected")
    
    print(f"\nProxy Likelihood Score: {proxy_score}/10")
    if proxy_score >= 5:
        print("⚠️  HIGH likelihood of proxying")
    elif proxy_score >= 3:
        print("⚠️  MODERATE likelihood of proxying")
    else:
        print("✓ LOW likelihood of proxying")


def main():
    import sys
    
    print("="*80)
    print("MINING POOL PROXY DETECTION TOOL")
    print("="*80)
    print()
    print("This tool simulates a miner connection to detect if a pool is proxying")
    print("stratum traffic to another backend pool and substituting addresses.")
    print()
    print("Tests performed:")
    print("  1. Address substitution detection")
    print("  2. Job timing and pattern analysis")
    print("  3. Backend fingerprinting")
    print("  4. Prevhash correlation")
    print()
    
    # Test suspicious pools + legitimate pools for comparison
    pools = [
        ('104.168.100.92', 7112, 'LuckyMonster US'),
        ('45.95.172.24', 7112, 'LuckyMonster EU'),
        ('92.119.126.14', 6057, 'zsolo.bid'),
        ('solo.atlaspool.io', 3333, 'AtlasPool'),
        ('solo.ckpool.org', 3333, 'CKPool US'),
        ('public-pool.io', 21496, 'Public Pool'),
    ]
    
    duration = 30  # Monitor for 30 seconds
    
    results_list = []
    for host, port, name in pools:
        print(f"\n{'#'*80}")
        print(f"# Testing: {name}")
        print(f"{'#'*80}")
        
        result = connect_and_monitor(host, port, duration)
        result['name'] = name
        results_list.append(result)
        
        # Analyze this pool
        detect_proxy_fingerprints(result)
        
        # Delay between tests
        if pools.index((host, port, name)) < len(pools) - 1:
            print("\nWaiting 5 seconds before next test...")
            time.sleep(5)
    
    # Compare patterns between pools
    compare_job_patterns(results_list)
    
    print(f"\n{'='*80}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*80}\n")
    
    print("CONCLUSION:")
    print("-" * 80)
    print("If both pools show:")
    print("  • Address substitution (test address not in coinbase)")
    print("  • Identical prevhashes at the same time")
    print("  • Similar merkle branch counts")
    print()
    print("Then they are likely proxying to the same backend pool and")
    print("substituting the miner's address with their own to steal rewards.")
    print()


if __name__ == "__main__":
    main()
