TLS material expected by the project:

- `ca.crt`: local CA certificate trusted by the client.
- `server.crt`: server certificate signed by `ca.crt`.
- `server.key`: private key for `server.crt`.

These files are not committed on purpose.

How to generate them (reproducible):

1. Install dependencies:
   `python -m pip install -r requirements.txt`
2. Generate certs (default: ECC / ECDSA P-256):
   `python scripts/generate_tls_certs.py --force`
3. Optional RSA fallback:
   `python scripts/generate_tls_certs.py --algorithm rsa --force`

Output directory: `config/tls/`
