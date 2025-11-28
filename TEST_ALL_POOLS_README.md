# test_all_pools.py - Comprehensive Pool Testing Script

## Overview

This script performs comprehensive testing of Bitcoin solo mining pools, collecting network information, performance metrics, and verification results.

## Features

- **IP Resolution**: Resolves hostname to IP address
- **ASN Lookup**: Gets ASN, ISP, country, and city information
- **Performance Testing**: Measures ping and stratum handshake times
- **Verification**: Tests if pool properly includes user address in coinbase
- **Dual Output**: Formatted table display + CSV export

## Usage

### Test All Pools

Test all pools listed in `pools.txt`:

```bash
python3 test_all_pools.py
```

### Test Single Pool

Test a specific pool:

```bash
python3 test_all_pools.py solo.atlaspool.io 3333
```

### Custom Test Address

Use a different Bitcoin address for testing:

```bash
python3 test_all_pools.py --address bc1qYOUR_ADDRESS_HERE
```

### Custom Output File

Specify a different CSV output file:

```bash
python3 test_all_pools.py --output my_results.csv
```

## pools.txt Format

The `pools.txt` file should contain one pool per line in the format:

```
hostname	port
```

Example:

```
solo.atlaspool.io	3333
solo.ckpool.org	3333
stratum.kano.is	3333
```

Lines starting with `#` are treated as comments and ignored.

## Output

### Console Output

The script displays:
- Progress for each pool (4 steps)
- Real-time results
- Formatted ASCII table with all results
- Summary statistics

Example:

```
Testing solo.atlaspool.io:3333...
  [1/4] Resolving IP address...
  ✓ IP: 166.117.239.148
  [2/4] Getting ASN information...
  ✓ ASN: AS16509 (Amazon.com, Inc.)
  [3/4] Running stratum speed test...
  ✓ Ping: 81ms
  ✓ Stratum: 189ms
  [4/4] Running address verification...
  ✅ Verification: PASSED
```

### CSV Output

The `results.csv` file contains:

| Column | Description |
|--------|-------------|
| hostname | Pool hostname |
| port | Pool port |
| ip | Resolved IP address |
| asn | Autonomous System Number |
| isp | Internet Service Provider name |
| country | Country location |
| city | City location |
| ping_ms | Ping time in milliseconds (or empty if N/A) |
| stratum_ms | Stratum handshake time in milliseconds (or empty if failed) |
| verification | Verification result: PASS, FAIL, UNKNOWN, ERROR, or TIMEOUT |

## Verification Results

- **PASS**: Pool correctly includes user address in coinbase (legitimate solo mining)
- **FAIL**: Pool does NOT include user address (may not be legitimate)
- **UNKNOWN**: Could not verify (pool may require valid credentials)
- **ERROR**: Error during verification
- **TIMEOUT**: Verification timed out (pool too slow)

## Dependencies

The script requires:
- Python 3.6+
- `stratum_test.py` (in same directory)
- `verify_pool.py` (in same directory)
- Internet connection (for ASN lookups)

## Performance

- Each pool takes approximately 30-60 seconds to test
- Tests run sequentially (not parallel)
- 1-second delay between pools to avoid API rate limits
- Total time for 16 pools: ~10-15 minutes

## Examples

### Test All Pools

```bash
python3 test_all_pools.py
```

Output:
```
Found 16 pools in pools.txt

[1/16] Testing solo.atlaspool.io:3333
...
[16/16] Testing btc.luckymonster.pro:7112
...

POOL TEST RESULTS
================================================================================
Hostname          | Port  | IP Address      | ASN     | ISP              | ...
--------------------------------------------------------------------------------
solo.atlaspool.io | 3333  | 166.117.239.148 | AS16509 | Amazon.com, Inc. | ...
...

Summary: 16 pools tested
  ✅ Passed: 12
  ❌ Failed: 2
  ⚠  Unknown: 1
  ❌ Errors: 1

Results saved to results.csv
```

### Test Single Pool

```bash
python3 test_all_pools.py solo-ca.solohash.co.uk 3333
```

### Test with Custom Address

```bash
python3 test_all_pools.py --address 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
```

## Troubleshooting

### "pools.txt not found"

Create a `pools.txt` file with your pool list:

```bash
echo "solo.atlaspool.io	3333" > pools.txt
echo "solo.ckpool.org	3333" >> pools.txt
```

### Slow Performance

This is normal. Each pool requires:
- DNS lookup
- ASN API call
- Stratum speed test (with retries)
- Full verification (with retries)

Total: 30-60 seconds per pool.

### Verification Timeouts

Some pools (like SoloHash) are slow to respond. The script uses:
- 30-second timeout per operation
- 2 automatic retries
- 120-second total timeout for verification

If a pool still times out, it will be marked as TIMEOUT in results.

### ASN Lookup Failures

The script uses ip-api.com for ASN lookups. If this fails:
- ASN will show as "N/A"
- Other tests will continue normally

## Notes

- The script is designed for temporary/ad-hoc testing
- Results are appended to CSV (overwrites existing file)
- No parallel execution (to avoid overwhelming pools)
- Respects pool servers with delays between tests

---

**Created**: November 25, 2025  
**Purpose**: Temporary testing script for pool analysis
