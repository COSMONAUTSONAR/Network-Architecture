# Network-Architecture
# NetArchitect - Recommendation & Config Engine (CIC-307 Mini-Project)

A Python CLI that takes a preset or custom network description, runs rule engines, and
outputs **(a)** a natural-language Architectural Rationale Log explaining every choice and
**(b)** deployment-ready Cisco IOS configs.

## Run (Python 3.9+, no third-party dependencies)
```bash
python -m netarchitect list                       # show the 3 presets
python -m netarchitect plan campus                # rationale log + subnet table
python -m netarchitect plan wan --out exports/wan # also write .cfg files
python -m netarchitect plan --json my_net.json    # custom parameters (schema: netarchitect/presets.py)
python -m netarchitect export-all                 # regenerate exports/campus|metro|wan
```
Invalid input exits with code 2 and a message (e.g. `PhysicalDistanceViolationError`).

## Tests
```bash
pip install pytest
pytest -v
```
Covers distance violations, address-space exhaustion, wildcard masks across edge-case
prefixes (/0-/32), host-to-prefix boundaries, zero-overlap, routing thresholds, config
contents and custom-parameter validation.

## Layout
| Path | Purpose |
|------|---------|
| `netarchitect/media.py` | L1 media engine: Cat6a <=100 m, OM4 101-400 m, OS2 >400 m, optical budget, boundary error |
| `netarchitect/vlsm.py` | Bitwise VLSM allocator, wildcard masks, summarisation |
| `netarchitect/routing.py` | OSPF single/multi-area, eBGP selection with RFC rationale |
| `netarchitect/engine.py` | Validation, hierarchical addressing, decisions (QoS, resiliency, L2) |
| `netarchitect/configs.py` | Cisco IOS generation: VLANs, SVIs, trunks, ACLs, OSPF, BGP, IPsec |
| `exports/<profile>/` | Generated `.cfg` files, `ALL_CONFIGS.txt`, `subnet_plan.txt`, `rationale_log.md` |
| `ai_audit_log.md` | AI code audit (4 documented flaws, diagnosis and fixes) |
| `docs/screenshots/` | Packet Tracer verification screenshots |

## Loading into Packet Tracer
Open each device's CLI, enter `enable` then `configure terminal`, and paste the matching
`exports/<profile>/<DEVICE>.cfg`. Replace `CHANGE_ME` secrets/PSKs first. On Packet Tracer's
3560/3650 use `Vlan` SVIs as generated; for the WAN profile use ISR routers (IPsec needs
the security license image).
Verify with: `show ip interface brief`, `show vlan brief`, `show ip route`,
`show ip ospf neighbor`, `show access-lists`, `show crypto isakmp sa`, `ping`.

## Repository
GitHub: _add your repository link here_
