# Security policy

## Scope

This project installs an owner-selected SSH public key on a FibreSeeker 3. Use
it only on a printer you own or are explicitly authorized to administer.

## Key handling

- Never put a private key in a `.fibrepack`.
- Never commit generated packages; they authorize a specific public key.
- Prefer a dedicated key for the printer.
- Revoke lost or retired keys promptly using [docs/REMOVE.md](docs/REMOVE.md).

The builder rejects files that resemble private keys, and the verifier checks
that generated packages contain no private-key marker.

## Reporting

Do not open a public issue containing printer credentials, private keys,
serial numbers, public IP addresses, VPN details, or complete diagnostic logs.
Report a vulnerability privately through GitHub's security-advisory feature.
