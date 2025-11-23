#!/bin/bash

# SSL Certificate Generation Script
# Supports both self-signed certificates (development) and Let's Encrypt (production)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
DOMAIN="${DOMAIN:-corporate-intel.example.com}"
CERT_TYPE="${CERT_TYPE:-self-signed}"
SSL_DIR="${SSL_DIR:-./config/ssl}"
EMAIL="${EMAIL:-admin@example.com}"

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

usage() {
    cat << EOF
SSL Certificate Generation Script

Usage: $0 [OPTIONS]

Options:
    -t, --type TYPE         Certificate type: self-signed or letsencrypt (default: self-signed)
    -d, --domain DOMAIN     Domain name (default: corporate-intel.example.com)
    -e, --email EMAIL       Email for Let's Encrypt (required for letsencrypt)
    -o, --output DIR        Output directory (default: ./config/ssl)
    -h, --help              Show this help message

Examples:
    # Generate self-signed certificate for development
    $0 --type self-signed --domain localhost

    # Generate Let's Encrypt certificate for production
    $0 --type letsencrypt --domain corporate-intel.com --email admin@corporate-intel.com

EOF
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            CERT_TYPE="$2"
            shift 2
            ;;
        -d|--domain)
            DOMAIN="$2"
            shift 2
            ;;
        -e|--email)
            EMAIL="$2"
            shift 2
            ;;
        -o|--output)
            SSL_DIR="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            ;;
    esac
done

generate_self_signed() {
    print_info "Generating self-signed SSL certificate for $DOMAIN"

    # Create SSL directory
    mkdir -p "$SSL_DIR"

    # Generate private key
    print_info "Generating private key..."
    openssl genrsa -out "$SSL_DIR/$DOMAIN.key" 4096

    # Generate certificate signing request
    print_info "Generating certificate signing request..."
    openssl req -new -key "$SSL_DIR/$DOMAIN.key" \
        -out "$SSL_DIR/$DOMAIN.csr" \
        -subj "/C=US/ST=State/L=City/O=Organization/OU=IT/CN=$DOMAIN" \
        -addext "subjectAltName = DNS:$DOMAIN,DNS:*.$DOMAIN,DNS:localhost,IP:127.0.0.1"

    # Generate self-signed certificate (valid for 365 days)
    print_info "Generating self-signed certificate (valid for 365 days)..."
    openssl x509 -req -days 365 \
        -in "$SSL_DIR/$DOMAIN.csr" \
        -signkey "$SSL_DIR/$DOMAIN.key" \
        -out "$SSL_DIR/$DOMAIN.crt" \
        -extensions v3_req \
        -extfile <(cat <<EOF
[v3_req]
subjectAltName = DNS:$DOMAIN,DNS:*.$DOMAIN,DNS:localhost,IP:127.0.0.1
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
EOF
)

    # Set proper permissions
    chmod 600 "$SSL_DIR/$DOMAIN.key"
    chmod 644 "$SSL_DIR/$DOMAIN.crt"

    print_info "Self-signed certificate generated successfully!"
    print_warning "This certificate is for DEVELOPMENT ONLY. Do not use in production."
    print_info ""
    print_info "Certificate files:"
    print_info "  Private Key: $SSL_DIR/$DOMAIN.key"
    print_info "  Certificate: $SSL_DIR/$DOMAIN.crt"
    print_info "  CSR: $SSL_DIR/$DOMAIN.csr"
    print_info ""
    print_info "To use with nginx, update your config with:"
    print_info "  ssl_certificate $SSL_DIR/$DOMAIN.crt;"
    print_info "  ssl_certificate_key $SSL_DIR/$DOMAIN.key;"
}

generate_letsencrypt() {
    print_info "Generating Let's Encrypt certificate for $DOMAIN"

    if [ -z "$EMAIL" ] || [ "$EMAIL" = "admin@example.com" ]; then
        print_error "Valid email address required for Let's Encrypt"
        print_error "Use: $0 --type letsencrypt --domain $DOMAIN --email your@email.com"
        exit 1
    fi

    # Check if certbot is installed
    if ! command -v certbot &> /dev/null; then
        print_error "certbot is not installed"
        print_info "Install certbot:"
        print_info "  Ubuntu/Debian: sudo apt-get install certbot"
        print_info "  macOS: brew install certbot"
        print_info "  or visit: https://certbot.eff.org/"
        exit 1
    fi

    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        print_warning "Let's Encrypt certificate generation typically requires root privileges"
        print_info "You may need to run: sudo $0 --type letsencrypt --domain $DOMAIN --email $EMAIL"
    fi

    # Detect web server
    if systemctl is-active --quiet nginx; then
        WEB_SERVER="nginx"
    elif systemctl is-active --quiet apache2; then
        WEB_SERVER="apache"
    else
        print_warning "No active web server detected. Using standalone mode."
        WEB_SERVER="standalone"
    fi

    print_info "Using $WEB_SERVER mode for certificate generation"

    # Generate certificate
    if [ "$WEB_SERVER" = "standalone" ]; then
        certbot certonly --standalone \
            --preferred-challenges http \
            --email "$EMAIL" \
            --agree-tos \
            --no-eff-email \
            -d "$DOMAIN"
    else
        certbot --"$WEB_SERVER" \
            --email "$EMAIL" \
            --agree-tos \
            --no-eff-email \
            -d "$DOMAIN"
    fi

    if [ $? -eq 0 ]; then
        print_info "Let's Encrypt certificate generated successfully!"
        print_info ""
        print_info "Certificate files (managed by certbot):"
        print_info "  Certificate: /etc/letsencrypt/live/$DOMAIN/fullchain.pem"
        print_info "  Private Key: /etc/letsencrypt/live/$DOMAIN/privkey.pem"
        print_info "  Chain: /etc/letsencrypt/live/$DOMAIN/chain.pem"
        print_info ""
        print_info "Certificates will auto-renew. Test renewal with:"
        print_info "  sudo certbot renew --dry-run"
    else
        print_error "Failed to generate Let's Encrypt certificate"
        exit 1
    fi
}

# Main execution
case $CERT_TYPE in
    self-signed)
        generate_self_signed
        ;;
    letsencrypt|lets-encrypt)
        generate_letsencrypt
        ;;
    *)
        print_error "Invalid certificate type: $CERT_TYPE"
        print_error "Valid types: self-signed, letsencrypt"
        exit 1
        ;;
esac

# Generate DH parameters for enhanced security (optional but recommended)
if [ "$CERT_TYPE" = "letsencrypt" ] || [ "$1" = "--with-dhparam" ]; then
    print_info "Generating Diffie-Hellman parameters (this may take a while)..."
    if [ "$CERT_TYPE" = "self-signed" ]; then
        openssl dhparam -out "$SSL_DIR/dhparam.pem" 2048
        print_info "DH parameters saved to: $SSL_DIR/dhparam.pem"
        print_info "Add to nginx config: ssl_dhparam $SSL_DIR/dhparam.pem;"
    else
        openssl dhparam -out /etc/letsencrypt/ssl-dhparams.pem 2048
        print_info "DH parameters saved to: /etc/letsencrypt/ssl-dhparams.pem"
    fi
fi

print_info ""
print_info "SSL certificate setup complete!"
print_info "Remember to reload your web server:"
print_info "  sudo systemctl reload nginx"
print_info "  or"
print_info "  docker-compose restart nginx"
