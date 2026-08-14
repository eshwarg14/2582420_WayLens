import sys
import argparse
import datetime
import ipaddress
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import Config


def ensure_ssl_certs() -> tuple[Path, Path]:
    cert_dir = Config.OUTPUTS_DIR
    cert_dir.mkdir(parents=True, exist_ok=True)
    cert_file = cert_dir / "cert.pem"
    key_file = cert_dir / "key.pem"

    if cert_file.exists() and key_file.exists():
        return cert_file, key_file

    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.primitives import serialization

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "WayLens Navigation"),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])

    san_list = [
        x509.DNSName("localhost"),
        x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
    ]
    try:
        local_ip = Config.get_local_ip()
        if local_ip not in ("127.0.0.1", "0.0.0.0"):
            san_list.append(x509.IPAddress(ipaddress.ip_address(local_ip)))
    except Exception:
        pass

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
        .add_extension(x509.SubjectAlternativeName(san_list), critical=False)
        .sign(key, hashes.SHA256())
    )

    with open(key_file, "wb") as f:
        f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    with open(cert_file, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    return cert_file, key_file


def start_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = False, use_ssl: bool = True):
    import uvicorn
    from server import app

    Config.ensure_dirs()
    local_ip = Config.get_local_ip()

    ssl_keyfile = None
    ssl_certfile = None
    protocol = "http"

    if use_ssl:
        try:
            cert_file, key_file = ensure_ssl_certs()
            ssl_certfile = str(cert_file)
            ssl_keyfile = str(key_file)
            protocol = "https"
        except Exception as e:
            print(f"Warning: Could not configure SSL certificates ({e}). Starting in HTTP mode.")
            protocol = "http"

    print("=" * 65)
    print("  WayLens: Generative AI Indoor Navigation Assistant")
    print("=" * 65)
    print(f"  Local Desktop Access : {protocol}://localhost:{port}")
    print(f"  Mobile Phone Access  : {protocol}://{local_ip}:{port}")
    print("=" * 65)
    if protocol == "https":
        print("  HTTPS Enabled: Required for mobile phone camera and mic access.")
    print("  Press Ctrl+C to terminate the server.\n")

    if ssl_certfile and ssl_keyfile:
        uvicorn.run(app, host=host, port=port, ssl_keyfile=ssl_keyfile, ssl_certfile=ssl_certfile)
    else:
        uvicorn.run(app, host=host, port=port)


def run_eval():
    from evaluation import run_full_evaluation
    run_full_evaluation()


def run_indexing():
    from build_embeddings import build_and_save_index
    build_and_save_index()


def main():
    parser = argparse.ArgumentParser(description="WayLens Indoor Navigation Assistant")
    parser.add_argument("--serve", action="store_true", default=True, help="Start web server")
    parser.add_argument("--eval", action="store_true", help="Run benchmark evaluation")
    parser.add_argument("--index", action="store_true", help="Rebuild CLIP embedding index")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host IP")
    parser.add_argument("--port", type=int, default=8000, help="Port number")
    parser.add_argument("--reload", action="store_true", help="Auto-reload on code change")
    parser.add_argument("--no-ssl", action="store_true", help="Run in HTTP mode instead of HTTPS")

    args = parser.parse_args()

    if args.eval:
        run_eval()
    elif args.index:
        run_indexing()
    else:
        start_server(host=args.host, port=args.port, reload=args.reload, use_ssl=not args.no_ssl)


if __name__ == "__main__":
    main()
