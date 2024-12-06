"""Generate a local CA and a leaf-signing helper.

Nothing here is novel; it exists so that the interception path is
mine end to end and I can see exactly where a handshake fails. The CA
key never leaves the machine and the generated cert is marked
clearly so it cannot be mistaken for anything else in a trust store.
"""
import argparse
import datetime as dt
import pathlib

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

CA_NAME = "sse-intercept local CA (do not trust outside a lab)"


def make_ca(outdir):
    outdir = pathlib.Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, CA_NAME),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "sse-intercept"),
    ])
    now = dt.datetime.now(dt.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=5))
        .not_valid_after(now + dt.timedelta(days=825))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0),
                       critical=True)
        .add_extension(x509.KeyUsage(
            digital_signature=True, key_cert_sign=True, crl_sign=True,
            content_commitment=False, key_encipherment=False,
            data_encipherment=False, key_agreement=False,
            encipher_only=False, decipher_only=False), critical=True)
        .sign(key, hashes.SHA256())
    )
    (outdir / "ca.key").write_bytes(key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption()))
    (outdir / "ca.key").chmod(0o600)
    (outdir / "ca.crt").write_bytes(
        cert.public_bytes(serialization.Encoding.PEM))
    return outdir / "ca.crt"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="ca")
    args = ap.parse_args()
    path = make_ca(args.dir)
    print(f"wrote {path}")
    print("import it into the client under test, nowhere else")


if __name__ == "__main__":
    main()
