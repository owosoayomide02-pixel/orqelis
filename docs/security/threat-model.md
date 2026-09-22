# Threat model (V1)

- External attacker against Orqelis infrastructure
- Malicious customer abusing security capabilities
- Compromised customer account
- Tampered endpoint agent
- Insider / founder access (mitigated by separate internal roles and no default telemetry access)
- AI prompt injection / unsafe recommendations (mitigated by redaction, structured output, no autonomous high-impact actions)
- Cross-tenant access (mitigated by organization_id filters and tests)
- Supply-chain compromise of dependencies
