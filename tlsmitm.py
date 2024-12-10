"""CONNECT handling and on-demand leaf certificates.

Leaf certs are cached in memory keyed on the SNI name. Generating one
per connection makes a chatty client take seconds to start, which
looks exactly like the kind of timing bug the tool is supposed to be
measuring, so the cache is not an optimisation, it is correctness of
the instrument.
"""
import datetime as dt
import pathlib
import ssl
import tempfile
import threading

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


class CertStore:

    def __init__(self, cadir="ca"):
        cadir = pathlib.Path(cadir)
        self.ca_cert = x509.load_pem_x509_certificate(
            (cadir / "ca.crt").read_bytes())
        self.ca_key = serialization.load_pem_private_key(
            (cadir / "ca.key").read_bytes(), password=None)
        self._lock = threading.Lock()
        self._cache = {}
        self._tmp = pathlib.Path(tempfile.mkdtemp(prefix="sseint-leaf-"))
        self._leaf_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048)

    def context_for(self, hostname):
        with self._lock:
            ctx = self._cache.get(hostname)
            if ctx is None:
                ctx = self._build(hostname)
                self._cache[hostname] = ctx
            return ctx

    def _build(self, hostname):
        now = dt.datetime.now(dt.timezone.utc)
        cert = (
            x509.CertificateBuilder()
            .subject_name(x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, hostname)]))
            .issuer_name(self.ca_cert.subject)
            .public_key(self._leaf_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - dt.timedelta(minutes=5))
            .not_valid_after(now + dt.timedelta(days=30))
            .add_extension(
                x509.SubjectAlternativeName([x509.DNSName(hostname)]),
                critical=False)
            .add_extension(x509.BasicConstraints(ca=False, path_length=None),
                           critical=True)
            .sign(self.ca_key, hashes.SHA256())
        )
        base = self._tmp / hostname.replace("/", "_")
        crt = base.with_suffix(".crt")
        key = base.with_suffix(".key")
        crt.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        key.write_bytes(self._leaf_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption()))
        key.chmod(0o600)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(certfile=str(crt), keyfile=str(key))
        return ctx


def client_context():
    """Upstream context. Verification stays on by default."""
    ctx = ssl.create_default_context()
    return ctx
