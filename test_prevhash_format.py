#!/usr/bin/env python3
"""
Test script to verify prevhash format from stratum vs blockchain explorer
"""

import socket
import json
import time
import requests

def get_prevhash_from_pool(host, port, address):
    """Get prevhash from a pool"""
    print(f"Connecting to {host}:{port}...")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    
    try:
        sock.connect((host, port))
        
        # Subscribe
        subscribe_msg = json.dumps({
            'id': 1,
            'method': 'mining.subscribe',
            'params': ['PrevhashTest/1.0']
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
        
        while time.time() - start_time < 10:
            chunk = sock.recv(4096).decode('utf-8')
            if not chunk:
                break
                
            buffer += chunk
            
            while '\n' in buffer:
                line, buffer = buffer.split('\n', 1)
                if line.strip():
                    try:
                        data = json.loads(line)
                        
                        # Check for mining.notify
                        if data.get('method') == 'mining.notify':
                            params = data.get('params', [])
                            if len(params) >= 9:
                                prevhash = params[1]
                                print(f"\n✓ Got prevhash from pool:")
                                print(f"  Raw: {prevhash}")
                                
                                # Reverse byte order for blockchain explorer
                                reversed_hash = ''.join([prevhash[i:i+2] for i in range(0, len(prevhash), 2)][::-1])
                                print(f"  Reversed: {reversed_hash}")
                                
                                sock.close()
                                return prevhash, reversed_hash
                    
                    except json.JSONDecodeError:
                        pass
        
        sock.close()
        return None, None
        
    except Exception as e:
        print(f"Error: {e}")
        if sock:
            sock.close()
        return None, None


def get_recent_blocks():
    """Get recent blocks from mempool.space"""
    print("\nFetching recent blocks from mempool.space...")
    
    try:
        response = requests.get('https://mempool.space/api/blocks', timeout=10)
        blocks = response.json()
        
        print(f"\n✓ Got {len(blocks)} recent blocks:")
        for i, block in enumerate(blocks[:5]):
            print(f"\n  Block {block['height']}:")
            print(f"    Hash: {block['id']}")
            print(f"    Time: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(block['timestamp']))}")
            if 'previousblockhash' in block:
                print(f"    Prev: {block['previousblockhash']}")
        
        return blocks
    
    except Exception as e:
        print(f"Error fetching blocks: {e}")
        return []


def main():
    print("="*80)
    print("PREVHASH FORMAT VERIFICATION")
    print("="*80)
    
    # Test with AtlasPool
    address = '3Ax2uht6S5Lh6V5HLNhxfaHnEZU7KaFvSZ'
    
    prevhash, reversed_hash = get_prevhash_from_pool('solo.atlaspool.io', 3333, address)
    
    if not prevhash:
        print("\n✗ Could not get prevhash from pool")
        return
    
    # Get recent blocks
    blocks = get_recent_blocks()
    
    if not blocks:
        print("\n✗ Could not get recent blocks")
        return
    
    # Compare
    print("\n" + "="*80)
    print("COMPARISON")
    print("="*80)
    
    print(f"\nPool prevhash (raw):      {prevhash}")
    print(f"Pool prevhash (reversed): {reversed_hash}")
    
    # Check if reversed hash matches any recent block
    found = False
    for block in blocks:
        if block['id'] == reversed_hash:
            print(f"\n✓ MATCH FOUND!")
            print(f"  Block height: {block['height']}")
            print(f"  Block hash: {block['id']}")
            print(f"  Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(block['timestamp']))}")
            found = True
            break
        
        # Also check if it matches previousblockhash
        if 'previousblockhash' in block and block['previousblockhash'] == reversed_hash:
            print(f"\n✓ MATCH FOUND (as previous block)!")
            print(f"  Next block height: {block['height']}")
            print(f"  Previous block hash: {block['previousblockhash']}")
            found = True
            break
    
    if not found:
        print(f"\n✗ NO MATCH FOUND in recent blocks")
        print(f"\nThis could mean:")
        print(f"  1. The block is older than the 15 most recent blocks")
        print(f"  2. There's a format issue with the prevhash")
        print(f"  3. The pool is not on the real Bitcoin blockchain")
        
        # Try searching mempool.space API
        print(f"\nTrying to search mempool.space for this block...")
        try:
            response = requests.get(f'https://mempool.space/api/block/{reversed_hash}', timeout=10)
            if response.status_code == 200:
                block_data = response.json()
                print(f"✓ FOUND via API!")
                print(f"  Block height: {block_data.get('height')}")
                print(f"  Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(block_data.get('timestamp', 0)))}")
            else:
                print(f"✗ Not found (HTTP {response.status_code})")
        except Exception as e:
            print(f"✗ API search failed: {e}")


if __name__ == "__main__":
    main()
