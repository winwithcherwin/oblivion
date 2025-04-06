import datetime
import os
import click

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import ec

PKI_DIR = ".secrets/pki"
CA_DIR = os.path.join(PKI_DIR, "root")
CA_KEY_PATH = os.path.join(CA_DIR, "oblivion-ca.key")
CA_CERT_PATH = os.path.join(CA_DIR, "oblivion-ca.crt")


@click.group()
def cli():
    """Manage PKI"""
    pass

@cli.command("init")
def do_init():
    """Initialise Oblivion Root Certificate Authority"""

    os.makedirs(CA_DIR, exist_ok=True)
    if os.path.exists(CA_KEY_PATH) or os.path.exists(CA_CERT_PATH):
        raise click.ClickException("Root CA already exists. Skipping  generation.")

    key = ec.generate_private_key(ec.SECP384R1())

    with open(CA_KEY_PATH, "wb") as f:
        f.write(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"NL"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"OBLIVION"),
        x509.NameAttribute(NameOID.COMMON_NAME, u"OBLIVION ROOT CA"),
    ])

    cert_builder = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow() - datetime.timedelta(minutes=5))
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=3650))  # 10 years
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None), critical=True,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False,
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(key.public_key()), critical=False,
        )
    )

    cert = cert_builder.sign(private_key=key, algorithm=hashes.SHA384())

    with open(CA_CERT_PATH, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

