#!/usr/bin/env python3
"""
Pool Traffic Analysis Tool

Analyzes stratum pool behavior to detect:
- Proxy destinations (by analyzing response patterns)
- Share submission behavior
- Work distribution patterns
- Connection fingerprinting
"""

import socket
import json
import time
import hashlib
import binascii
from typing import Dict, List, Tuple

def analyze_pool_behavior(host: str, port: int, name: str) -> Dict:
    """
    Perform deep analysis of pool behavior
    """
    print(f"\n{'='*80}")
    print(f"ANALYZING: {name} ({host}:{port})")
    print(f"{'='*80}\n")
    
    results = {
        'name': name,
        'host': host,
        'port': port,
        'tests': {}
    }
    
    # Test 1: Connection timing
    print("[1/6] Connection Timing Analysis...")
    connect_times = []
    for i in range(3):
        start = time.time()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, port))
            elapsed = time.time() - start
            connect_times.append(elapsed)
            sock.close()
        except:
            connect_times.append(None)
        time.sleep(0.5)
    
    avg_connect = sum(t for t in connect_times if t) / len([t for t in connect_times if t]) if any(connect_times) else None
    print(f"  Average connect time: {avg_connect:.3f}s" if avg_connect else "  Failed to connect")
    results['tests']['connect_time'] = avg_connect
    
    # Test 2: Subscribe response analysis
    print("\n[2/6] Subscribe Response Analysis...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))
        
        # Send subscribe with specific user agent
        subscribe_msg = json.dumps({
            'id': 1,
            'method': 'mining.subscribe',
            'params': ['PoolAnalyzer/1.0']
        }) + '\n'
        
        send_time = time.time()
        sock.sendall(subscribe_msg.encode('utf-8'))
        
        # Measure response time
        response = sock.recv(4096).decode('utf-8')
        response_time = time.time() - send_time
        
        print(f"  Response time: {response_time:.3f}s")
        results['tests']['subscribe_response_time'] = response_time
        
        # Parse response
        for line in response.split('\n'):
            if line.strip():
                try:
                    data = json.loads(line)
                    if data.get('id') == 1:
                        result = data.get('result', [])
                        if len(result) >= 2:
                            extranonce1 = result[1]
                            extranonce2_size = result[2] if len(result) > 2 else None
                            print(f"  Extranonce1: {extranonce1} ({len(extranonce1)//2} bytes)")
                            print(f"  Extranonce2 size: {extranonce2_size}")
                            results['tests']['extranonce1_size'] = len(extranonce1)//2
                            results['tests']['extranonce2_size'] = extranonce2_size
                except:
                    pass
        
        sock.close()
    except Exception as e:
        print(f"  Error: {e}")
    
    # Test 3: Multiple job analysis
    print("\n[3/6] Job Distribution Analysis...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(15)
        sock.connect((host, port))
        
        subscribe_msg = json.dumps({'id': 1, 'method': 'mining.subscribe', 'params': []}) + '\n'
        sock.sendall(subscribe_msg.encode('utf-8'))
        time.sleep(0.3)
        
        authorize_msg = json.dumps({'id': 2, 'method': 'mining.authorize', 'params': ['test', 'x']}) + '\n'
        sock.sendall(authorize_msg.encode('utf-8'))
        
        # Collect multiple jobs
        jobs = []
        start_time = time.time()
        buffer = ""
        
        while time.time() - start_time < 10:
            try:
                chunk = sock.recv(4096).decode('utf-8')
                buffer += chunk
                
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    if 'mining.notify' in line:
                        try:
                            data = json.loads(line)
                            if 'params' in data:
                                jobs.append(data['params'])
                        except:
                            pass
            except socket.timeout:
                break
        
        print(f"  Received {len(jobs)} job(s) in 10 seconds")
        results['tests']['jobs_per_10s'] = len(jobs)
        
        # Analyze job uniqueness
        if len(jobs) > 1:
            prevhashes = [j[1] for j in jobs]
            unique_prevhashes = len(set(prevhashes))
            print(f"  Unique prevhashes: {unique_prevhashes}")
            results['tests']['unique_prevhashes'] = unique_prevhashes
        
        sock.close()
    except Exception as e:
        print(f"  Error: {e}")
    
    # Test 4: Invalid share submission
    print("\n[4/6] Share Submission Behavior...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))
        
        subscribe_msg = json.dumps({'id': 1, 'method': 'mining.subscribe', 'params': []}) + '\n'
        sock.sendall(subscribe_msg.encode('utf-8'))
        time.sleep(0.3)
        
        authorize_msg = json.dumps({'id': 2, 'method': 'mining.authorize', 'params': ['test', 'x']}) + '\n'
        sock.sendall(authorize_msg.encode('utf-8'))
        time.sleep(0.5)
        
        # Submit invalid share
        submit_msg = json.dumps({
            'id': 3,
            'method': 'mining.submit',
            'params': ['test', 'job123', '00000000', '00000000', '00000000']
        }) + '\n'
        
        sock.sendall(submit_msg.encode('utf-8'))
        time.sleep(0.5)
        
        response = sock.recv(4096).decode('utf-8')
        
        # Check response
        for line in response.split('\n'):
            if '"id":3' in line or '"id": 3' in line:
                try:
                    data = json.loads(line)
                    if 'error' in data and data['error']:
                        print(f"  Share rejected (expected): {data['error']}")
                        results['tests']['share_rejection'] = 'proper'
                    elif 'result' in data:
                        if data['result'] == True:
                            print(f"  ⚠️  WARNING: Invalid share ACCEPTED!")
                            results['tests']['share_rejection'] = 'accepts_invalid'
                        else:
                            print(f"  Share rejected properly")
                            results['tests']['share_rejection'] = 'proper'
                except:
                    pass
        
        sock.close()
    except Exception as e:
        print(f"  Error: {e}")
    
    # Test 5: Reconnection behavior
    print("\n[5/6] Reconnection Pattern Analysis...")
    reconnect_times = []
    for i in range(3):
        try:
            start = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((host, port))
            
            subscribe_msg = json.dumps({'id': 1, 'method': 'mining.subscribe', 'params': []}) + '\n'
            sock.sendall(subscribe_msg.encode('utf-8'))
            
            response = sock.recv(4096)
            elapsed = time.time() - start
            reconnect_times.append(elapsed)
            
            sock.close()
        except:
            reconnect_times.append(None)
        time.sleep(0.5)
    
    valid_times = [t for t in reconnect_times if t]
    if valid_times:
        import statistics
        avg = statistics.mean(valid_times)
        stddev = statistics.stdev(valid_times) if len(valid_times) > 1 else 0
        print(f"  Average: {avg:.3f}s, StdDev: {stddev:.3f}s")
        results['tests']['reconnect_variance'] = stddev
    
    # Test 6: Coinbase analysis
    print("\n[6/6] Coinbase Structure Analysis...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))
        
        subscribe_msg = json.dumps({'id': 1, 'method': 'mining.subscribe', 'params': []}) + '\n'
        sock.sendall(subscribe_msg.encode('utf-8'))
        time.sleep(0.3)
        
        authorize_msg = json.dumps({'id': 2, 'method': 'mining.authorize', 'params': ['bc1qtest', 'x']}) + '\n'
        sock.sendall(authorize_msg.encode('utf-8'))
        time.sleep(0.5)
        
        data = sock.recv(8192).decode('utf-8')
        
        for line in data.split('\n'):
            if 'mining.notify' in line and 'params' in line:
                try:
                    msg = json.loads(line)
                    params = msg['params']
                    coinb1 = params[2]
                    coinb2 = params[3]
                    
                    cb1 = binascii.unhexlify(coinb1)
                    cb2 = binascii.unhexlify(coinb2)
                    
                    print(f"  Coinb1: {len(cb1)} bytes")
                    print(f"  Coinb2: {len(cb2)} bytes")
                    
                    # Check for pool signature
                    readable1 = ''.join(chr(b) if 32 <= b < 127 else '' for b in cb1)
                    readable2 = ''.join(chr(b) if 32 <= b < 127 else '' for b in cb2)
                    
                    if readable1:
                        print(f"  Readable in coinb1: {readable1}")
                    if readable2:
                        print(f"  Readable in coinb2: {readable2}")
                    
                    results['tests']['coinb1_size'] = len(cb1)
                    results['tests']['coinb2_size'] = len(cb2)
                    
                    break
                except:
                    pass
        
        sock.close()
    except Exception as e:
        print(f"  Error: {e}")
    
    return results


def compare_pools(results_list: List[Dict]):
    """Compare multiple pool results to find similarities"""
    print(f"\n{'='*80}")
    print("COMPARATIVE ANALYSIS")
    print(f"{'='*80}\n")
    
    # Compare extranonce sizes
    print("Extranonce Configuration:")
    for r in results_list:
        name = r['name']
        en1 = r['tests'].get('extranonce1_size', 'N/A')
        en2 = r['tests'].get('extranonce2_size', 'N/A')
        print(f"  {name:20} EN1: {en1} bytes, EN2: {en2} bytes")
    
    # Compare response times
    print("\nResponse Times:")
    for r in results_list:
        name = r['name']
        sub_time = r['tests'].get('subscribe_response_time', None)
        if sub_time:
            print(f"  {name:20} {sub_time:.3f}s")
    
    # Compare coinbase sizes
    print("\nCoinbase Sizes:")
    for r in results_list:
        name = r['name']
        cb1 = r['tests'].get('coinb1_size', 'N/A')
        cb2 = r['tests'].get('coinb2_size', 'N/A')
        print(f"  {name:20} CB1: {cb1} bytes, CB2: {cb2} bytes")
    
    # Look for identical patterns
    print("\nSuspicious Similarities:")
    
    # Check if extranonce configs match
    en_configs = {}
    for r in results_list:
        en1 = r['tests'].get('extranonce1_size')
        en2 = r['tests'].get('extranonce2_size')
        if en1 and en2:
            key = f"{en1},{en2}"
            if key not in en_configs:
                en_configs[key] = []
            en_configs[key].append(r['name'])
    
    for config, pools in en_configs.items():
        if len(pools) > 1:
            print(f"  ⚠️  Identical extranonce config ({config}): {', '.join(pools)}")
    
    # Check if coinbase sizes match
    cb_sizes = {}
    for r in results_list:
        cb1 = r['tests'].get('coinb1_size')
        cb2 = r['tests'].get('coinb2_size')
        if cb1 and cb2:
            key = f"{cb1},{cb2}"
            if key not in cb_sizes:
                cb_sizes[key] = []
            cb_sizes[key].append(r['name'])
    
    for sizes, pools in cb_sizes.items():
        if len(pools) > 1:
            print(f"  ⚠️  Identical coinbase sizes ({sizes}): {', '.join(pools)}")


def main():
    import sys
    
    print("="*80)
    print("POOL TRAFFIC ANALYSIS TOOL")
    print("="*80)
    print()
    print("This tool performs deep analysis of pool behavior to detect:")
    print("  • Proxy patterns")
    print("  • Share submission behavior")
    print("  • Connection fingerprinting")
    print("  • Suspicious similarities between pools")
    print()
    
    # Test the suspicious pools
    pools = [
        ('104.168.100.92', 7112, 'LuckyMonster'),
        ('92.119.126.14', 6057, 'zsolo.bid'),
    ]
    
    # Optionally add comparison pools
    if '--compare' in sys.argv:
        pools.extend([
            ('solo-ca.solohash.co.uk', 3333, 'SoloHash'),
            ('solo.ckpool.org', 3333, 'CKPool'),
        ])
    
    results = []
    for host, port, name in pools:
        result = analyze_pool_behavior(host, port, name)
        results.append(result)
        time.sleep(2)  # Delay between tests
    
    # Compare results
    compare_pools(results)
    
    print(f"\n{'='*80}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
