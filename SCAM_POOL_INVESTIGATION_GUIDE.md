# Scam Pool Investigation Guide

## Pools Under Investigation

- **LuckyMonster**: 104.168.100.92:7112 (btc.luckymonster.pro)
- **zsolo.bid**: 92.119.126.14:6057

## Methods to Gather Hard Proof

### 1. Blockchain Analysis (STRONGEST PROOF) ⭐⭐⭐

**What to check**: Look up the payout addresses on blockchain explorers

**Payout Addresses**:
- LuckyMonster: `1CS1Zq3mcU4vgEonNxS6R3WfHHB4tTt3sx`
- zsolo.bid: `1Kru6EgGtM6FVYU8V1QTH2Kek7gESakBQY`

**Where to check**:
- https://blockchair.com/bitcoin/address/1CS1Zq3mcU4vgEonNxS6R3WfHHB4tTt3sx
- https://blockchair.com/bitcoin/address/1Kru6EgGtM6FVYU8V1QTH2Kek7gESakBQY
- https://mempool.space/address/1CS1Zq3mcU4vgEonNxS6R3WfHHB4tTt3sx
- https://mempool.space/address/1Kru6EgGtM6FVYU8V1QTH2Kek7gESakBQY

**What to look for**:
1. **Coinbase transactions** (block rewards) - These are 3.125+ BTC transactions
2. **When they started** - First coinbase transaction date
3. **How many blocks** - Total number of blocks found
4. **Total stolen** - Sum of all coinbase transactions

**Smoking Gun**: If these addresses have received coinbase transactions, it proves they found blocks and kept the rewards instead of paying miners.

### 2. Miner Testimony ⭐⭐⭐

**What to do**: Find miners who used these pools

**Questions to ask**:
1. Did you ever receive a payout?
2. Did the pool claim you found a block?
3. Do you have screenshots of your mining dashboard?
4. What address did you mine to?
5. Can you check if that address received any payments?

**Where to find miners**:
- BitcoinTalk forums
- Reddit r/BitcoinMining
- Discord mining communities
- Pool's own chat/forum (if they have one)

### 3. Traffic Analysis ⭐⭐

**Tool**: `analyze_pool_traffic.py` (created above)

**What it tests**:
- Connection patterns
- Share submission behavior
- Job distribution
- Response timing
- Coinbase structure

**Run it**:
```bash
python3 analyze_pool_traffic.py
python3 analyze_pool_traffic.py --compare  # Include legitimate pools for comparison
```

**What to look for**:
- Identical patterns between suspicious pools
- Unusual share acceptance (accepting invalid shares)
- Suspicious response times (indicating proxy)

### 4. DNS/Network Investigation ⭐⭐

**Check domain ownership**:
```bash
whois btc.luckymonster.pro
whois zsolo.bid
```

**Check IP ownership**:
```bash
whois 104.168.100.92
whois 92.119.126.14
```

**Look for**:
- Same registrar
- Same nameservers
- Same hosting provider
- Same registration date
- Privacy protection (hiding identity)

### 5. Historical Block Analysis ⭐⭐⭐

**What to do**: Search blockchain for blocks with their pool signatures

**Pool signatures**:
- LuckyMonster: "49l3"
- zsolo.bid: "4"

**How to search**:
1. Use blockchain explorer's search function
2. Look for coinbase transactions containing these signatures
3. Check where the rewards went

**Tools**:
- https://blockchair.com/bitcoin/blocks
- https://mempool.space/blocks
- Bitcoin Core RPC: `bitcoin-cli getblock <blockhash> 2`

### 6. Traceroute Analysis ⭐

**What to do**: Trace network path to pools

```bash
traceroute 104.168.100.92
traceroute 92.119.126.14
```

**Look for**:
- Similar network paths
- Same upstream providers
- Geographic location
- Unusual routing (indicating proxy)

### 7. SSL/TLS Certificate Analysis ⭐

**If pools use SSL**:
```bash
openssl s_client -connect btc.luckymonster.pro:7112 -showcerts
openssl s_client -connect zsolo.bid:6057 -showcerts
```

**Look for**:
- Same certificate authority
- Same organization
- Same certificate serial numbers
- Wildcard certificates (*.domain.com)

### 8. Social Media Investigation ⭐

**Check**:
- Twitter/X accounts
- Telegram groups
- Discord servers
- Reddit posts
- BitcoinTalk threads

**Look for**:
- Who operates them
- User complaints
- Payout proof (or lack thereof)
- Suspicious activity

### 9. Code Fingerprinting ⭐⭐

**What to analyze**:
- Stratum protocol responses
- Error messages
- JSON formatting
- Subscription IDs format
- Job ID format

**Example**:
```python
# LuckyMonster subscription ID: "0HNH4AGN1JJ3C"
# zsolo.bid subscription ID:    "0HNH4ADM3VS28"
# Pattern: 0HNH + random chars
```

If both use the same ID format, they likely use the same software.

### 10. Honeypot Test ⭐⭐⭐

**What to do**: Actually mine on the pool with a test miner

**Steps**:
1. Set up a small miner (even CPU mining)
2. Point it at the suspicious pool
3. Mine for 24-48 hours
4. Monitor if you receive ANY payouts
5. Check if your address appears in any blocks

**This is definitive proof**: If you mine and never receive payouts, it's a scam.

## Evidence Checklist

### Already Confirmed ✅

- [x] Pools pay to their own addresses, not miner addresses
- [x] Address verification fails (miner address not in coinbase)
- [x] Minimal pool signatures (hiding identity)
- [x] Both use P2PKH (legacy) payout addresses

### To Investigate 🔍

- [ ] Blockchain history of payout addresses
- [ ] Miner testimonies
- [ ] Domain/IP ownership
- [ ] Historical block analysis
- [ ] Actual mining test (honeypot)

## Legal Considerations

**Before publishing accusations**:

1. **Document everything** - Screenshots, logs, blockchain evidence
2. **Get multiple sources** - Don't rely on single piece of evidence
3. **Consult lawyer** - Defamation laws vary by jurisdiction
4. **Use factual language** - "Pool pays to address X" not "Pool is stealing"
5. **Offer right to respond** - Contact pool operators for comment

## Reporting

**Where to report**:
1. **BitcoinTalk** - Post in Scam Accusations forum
2. **Reddit** - r/BitcoinMining, r/Bitcoin
3. **Mining Pool Lists** - Request removal from pool directories
4. **Social Media** - Warn other miners

**What to include**:
- Blockchain evidence (links to addresses)
- Verification test results
- Miner testimonies (if available)
- Technical analysis
- Timeline of investigation

## Example Report Template

```
SCAM POOL WARNING: [Pool Name]

Pool: [name] ([host]:[port])
Payout Address: [address]

EVIDENCE:
1. Address Verification: FAILED
   - Pool pays to: [address]
   - Miner address: NOT INCLUDED in coinbase

2. Blockchain Analysis:
   - Payout address has received [X] coinbase transactions
   - Total value: [X] BTC
   - Blocks found: [list block heights]
   - No evidence of payouts to miners

3. Technical Analysis:
   - [findings from verify_pool.py]
   - [findings from traffic analysis]

4. Miner Testimonies:
   - [quotes from affected miners]

CONCLUSION:
This pool does not pay miners. Block rewards go to pool-controlled
address [address]. Miners should avoid this pool.

PROOF:
- Blockchain: [links]
- Verification: [screenshots]
- Technical: [logs]
```

---

**Created**: November 25, 2025  
**Purpose**: Investigation guide for suspected scam pools
