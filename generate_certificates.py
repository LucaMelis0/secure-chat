from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from datetime import datetime, timedelta


def generate_certificates():
    """
    Generates a self-signed CA certificate and saves the private key and certificate to files.
    """
    CURRENT_TIME = datetime.now()
    OWNER = "ADMIN"

    # Generate RSA private key for the CA
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=4096
    )

    # CA certificate details
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"IT"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"Sardinia"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"Cagliari"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Organization"),
        x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, u"Organization Development CA"),
        x509.NameAttribute(NameOID.COMMON_NAME, f"Organization CA - {OWNER}"),
        x509.NameAttribute(NameOID.EMAIL_ADDRESS, u"help@organization.it"),
    ])

    # Generate the certificate
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        CURRENT_TIME
    ).not_valid_after(
        CURRENT_TIME + timedelta(days=3650)  # 10 years validity
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName(u"localhost"),
            x509.DNSName(u"127.0.0.1"),
            x509.DNSName(u"::1"),
        ]),
        critical=False,
    ).add_extension(
        x509.BasicConstraints(ca=True, path_length=None),
        critical=True
    ).add_extension(
        x509.KeyUsage(
            digital_signature=True,
            key_encipherment=True,
            key_cert_sign=True,
            crl_sign=True,
            content_commitment=False,
            data_encipherment=False,
            key_agreement=False,
            encipher_only=False,
            decipher_only=False
        ),
        critical=True
    ).add_extension(
        x509.ExtendedKeyUsage([
            ExtendedKeyUsageOID.SERVER_AUTH,
            ExtendedKeyUsageOID.CLIENT_AUTH
        ]),
        critical=False
    ).add_extension(
        x509.SubjectKeyIdentifier.from_public_key(private_key.public_key()),
        critical=False
    ).add_extension(
        x509.AuthorityKeyIdentifier.from_issuer_public_key(private_key.public_key()),
        critical=False
    ).sign(private_key, hashes.SHA256())

    # Save the private key
    with open("key.pem", "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))

    # Save the certificate
    with open("cert.pem", "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

    print("Certificate generated successfully!")
    print(f"- Owner: Organization CA - {OWNER}")
    print("- Validity: 10 years")
    print(f"- Creation date: {CURRENT_TIME.strftime('%Y-%m-%d %H:%M:%S')}")
    print("- Generated files: cert.pem, key.pem")


if __name__ == "__main__":
    generate_certificates()