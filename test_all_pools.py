#!/usr/bin/env python3
"""
Comprehensive Pool Testing Script

Tests all pools in pools.txt (or a single pool from command line) and collects:
- IP address
- ASN information
- Ping time
- Stratum handshake time
- Address verification result

Outputs to formatted table and results.csv
"""

import socket
import subprocess
import json
import sys
import argparse
import csv
import re
from typing import Optional, Dict, Tuple


def get_ip_address(hostname: str) -> Optional[str]:
    """Resolve hostname to IP address"""
    try:
        ip = socket.gethostbyname(hostname)
        return ip
    except socket.gaierror:
        return None


def get_asn_info(ip: str) -> Dict[str, str]:
    """Get ASN information for an IP address using ip-api.com"""
    import urllib.request
    import urllib.error
    
    try:
        url = f'http://ip-api.com/json/{ip}?fields=status,as,isp,org,country,city'
        req = urllib.request.Request(url, headers={'User-Agent': 'PoolTester/1.0'})
        
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            if data.get('status') == 'success':
                as_info = data.get('as', '')
                asn = ''
                if as_info.startswith('AS'):
                    asn = as_info.split()[0]
                
                return {
                    'asn': asn,
                    'isp': data.get('isp', ''),
                    'org': data.get('org', ''),
                    'country': data.get('country', ''),
                    'city': data.get('city', '')
                }
    except Exception as e:
        pass
    
    return {
        'asn': 'N/A',
        'isp': 'N/A',
        'org': 'N/A',
        'country': 'N/A',
        'city': 'N/A'
    }


def run_stratum_test(hostname: str, port: int) -> Tuple[Optional[float], Optional[float]]:
    """
    Run stratum_test.py and extract ping and stratum times.
    Returns (ping_ms, stratum_ms)
    """
    try:
        result = subprocess.run(
            ['python3', 'stratum_test.py', hostname, str(port)],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output = result.stdout
        
        # Parse the output table to extract times
        ping_time = None
        stratum_time = None
        
        # Look for the data row in the table
        for line in output.split('\n'):
            if hostname in line and '|' in line:
                # Split by | and extract values
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 7:
                    # Format: | Pool Name | CC | Host | Port | Ping (ms) | Stratum (ms) |
                    ping_str = parts[5]
                    stratum_str = parts[6]
                    
                    # Parse ping time
                    if ping_str and ping_str not in ['BLOCKED', 'N/A', '']:
                        try:
                            # Handle "123 (120-125)" format
                            ping_time = float(ping_str.split()[0])
                        except:
                            pass
                    
                    # Parse stratum time
                    if stratum_str and stratum_str not in ['N/A', '']:
                        try:
                            stratum_time = float(stratum_str.split()[0])
                        except:
                            pass
                    
                    break
        
        return (ping_time, stratum_time)
        
    except subprocess.TimeoutExpired:
        return (None, None)
    except Exception as e:
        return (None, None)


def run_verify_pool(hostname: str, port: int, test_address: str) -> str:
    """
    Run verify_pool.py and determine if address verification passed.
    Returns: "PASS", "FAIL", "UNKNOWN", or "ERROR"
    """
    try:
        result = subprocess.run(
            ['python3', 'verify_pool.py', hostname, str(port), test_address, 
             '--timeout', '30', '--retries', '2'],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        output = result.stdout
        
        # Check for verification result
        if '✅ VERIFICATION PASSED' in output:
            return 'PASS'
        elif '❌ VERIFICATION FAILED' in output:
            return 'FAIL'
        elif '⚠️  Unknown' in output or 'Could not verify' in output:
            return 'UNKNOWN'
        else:
            return 'ERROR'
        
    except subprocess.TimeoutExpired:
        return 'TIMEOUT'
    except Exception as e:
        return 'ERROR'


def test_pool(hostname: str, port: int, test_address: str) -> Dict:
    """Test a single pool and return all results"""
    print(f"\nTesting {hostname}:{port}...")
    
    # Get IP address
    print(f"  [1/4] Resolving IP address...")
    ip = get_ip_address(hostname)
    if not ip:
        print(f"  ❌ Could not resolve hostname")
        return {
            'hostname': hostname,
            'port': port,
            'ip': 'N/A',
            'asn': 'N/A',
            'isp': 'N/A',
            'country': 'N/A',
            'ping_ms': None,
            'stratum_ms': None,
            'verification': 'ERROR'
        }
    
    print(f"  ✓ IP: {ip}")
    
    # Get ASN info
    print(f"  [2/4] Getting ASN information...")
    asn_info = get_asn_info(ip)
    print(f"  ✓ ASN: {asn_info['asn']} ({asn_info['isp']})")
    
    # Run stratum test
    print(f"  [3/4] Running stratum speed test...")
    ping_ms, stratum_ms = run_stratum_test(hostname, port)
    if ping_ms:
        print(f"  ✓ Ping: {ping_ms:.0f}ms")
    else:
        print(f"  ⚠ Ping: N/A")
    if stratum_ms:
        print(f"  ✓ Stratum: {stratum_ms:.0f}ms")
    else:
        print(f"  ❌ Stratum: Failed")
    
    # Run verification
    print(f"  [4/4] Running address verification...")
    verification = run_verify_pool(hostname, port, test_address)
    if verification == 'PASS':
        print(f"  ✅ Verification: PASSED")
    elif verification == 'FAIL':
        print(f"  ❌ Verification: FAILED")
    elif verification == 'UNKNOWN':
        print(f"  ⚠ Verification: UNKNOWN")
    else:
        print(f"  ❌ Verification: {verification}")
    
    return {
        'hostname': hostname,
        'port': port,
        'ip': ip,
        'asn': asn_info['asn'],
        'isp': asn_info['isp'],
        'country': asn_info['country'],
        'city': asn_info['city'],
        'ping_ms': ping_ms,
        'stratum_ms': stratum_ms,
        'verification': verification
    }


def print_results_table(results: list):
    """Print results in a formatted ASCII table"""
    if not results:
        return
    
    print("\n" + "=" * 140)
    print("POOL TEST RESULTS")
    print("=" * 140)
    print()
    
    # Calculate column widths
    max_host = max(len(r['hostname']) for r in results)
    max_host = max(max_host, len("Hostname"))
    
    max_ip = max(len(r['ip']) for r in results)
    max_ip = max(max_ip, len("IP Address"))
    
    max_asn = max(len(r['asn']) for r in results)
    max_asn = max(max_asn, len("ASN"))
    
    max_isp = max(len(r['isp'][:30]) for r in results)
    max_isp = max(max_isp, len("ISP"))
    max_isp = min(max_isp, 30)  # Cap at 30
    
    # Header
    print(f"{'Hostname':<{max_host}} | {'Port':<5} | {'IP Address':<{max_ip}} | {'ASN':<{max_asn}} | {'ISP':<{max_isp}} | {'Ping':<6} | {'Stratum':<8} | {'Verify':<8}")
    print("-" * 140)
    
    # Data rows
    for r in results:
        hostname = r['hostname']
        port = str(r['port'])
        ip = r['ip']
        asn = r['asn']
        isp = r['isp'][:30] if len(r['isp']) > 30 else r['isp']
        ping = f"{r['ping_ms']:.0f}ms" if r['ping_ms'] else "N/A"
        stratum = f"{r['stratum_ms']:.0f}ms" if r['stratum_ms'] else "N/A"
        verify = r['verification']
        
        print(f"{hostname:<{max_host}} | {port:<5} | {ip:<{max_ip}} | {asn:<{max_asn}} | {isp:<{max_isp}} | {ping:<6} | {stratum:<8} | {verify:<8}")
    
    print()
    
    # Summary
    total = len(results)
    passed = sum(1 for r in results if r['verification'] == 'PASS')
    failed = sum(1 for r in results if r['verification'] == 'FAIL')
    unknown = sum(1 for r in results if r['verification'] == 'UNKNOWN')
    errors = sum(1 for r in results if r['verification'] in ['ERROR', 'TIMEOUT'])
    
    print(f"Summary: {total} pools tested")
    print(f"  ✅ Passed: {passed}")
    print(f"  ❌ Failed: {failed}")
    print(f"  ⚠  Unknown: {unknown}")
    print(f"  ❌ Errors: {errors}")
    print()


def save_to_csv(results: list, filename: str = 'results.csv'):
    """Save results to CSV file"""
    if not results:
        return
    
    with open(filename, 'w', newline='') as csvfile:
        fieldnames = ['hostname', 'port', 'ip', 'asn', 'isp', 'country', 'city', 
                      'ping_ms', 'stratum_ms', 'verification']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for result in results:
            writer.writerow(result)
    
    print(f"Results saved to {filename}")


def main():
    parser = argparse.ArgumentParser(
        description='Test solo mining pools for connectivity and verification',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Test all pools in pools.txt:
    python3 test_all_pools.py
  
  Test a single pool:
    python3 test_all_pools.py solo.atlaspool.io 3333
  
  Test with custom address:
    python3 test_all_pools.py --address bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh
        """
    )
    
    parser.add_argument('hostname', nargs='?', help='Pool hostname (optional)')
    parser.add_argument('port', nargs='?', type=int, help='Pool port (optional)')
    parser.add_argument('--address', default='bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh',
                        help='Bitcoin address to test (default: bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh)')
    parser.add_argument('--output', default='results.csv',
                        help='Output CSV filename (default: results.csv)')
    
    args = parser.parse_args()
    
    print("=" * 140)
    print("SOLO MINING POOL COMPREHENSIVE TEST")
    print("=" * 140)
    print()
    print("This script tests pools for:")
    print("  • IP address resolution")
    print("  • ASN and ISP information")
    print("  • Ping and stratum connection times")
    print("  • Address verification (solo mining legitimacy)")
    print()
    print(f"Test address: {args.address}")
    print("=" * 140)
    
    results = []
    
    # Single pool mode
    if args.hostname and args.port:
        result = test_pool(args.hostname, args.port, args.address)
        results.append(result)
    
    # Multi-pool mode (read from pools.txt)
    else:
        try:
            with open('pools.txt', 'r') as f:
                pools = []
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = line.split()
                        if len(parts) >= 2:
                            hostname = parts[0]
                            port = int(parts[1])
                            pools.append((hostname, port))
                
                print(f"\nFound {len(pools)} pools in pools.txt")
                
                for i, (hostname, port) in enumerate(pools, 1):
                    print(f"\n[{i}/{len(pools)}] Testing {hostname}:{port}")
                    result = test_pool(hostname, port, args.address)
                    results.append(result)
                    
                    # Small delay between tests to be nice to APIs
                    if i < len(pools):
                        import time
                        time.sleep(1)
        
        except FileNotFoundError:
            print("Error: pools.txt not found")
            print("Please create pools.txt with format: hostname port")
            return 1
    
    # Print results
    print_results_table(results)
    
    # Save to CSV
    save_to_csv(results, args.output)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
