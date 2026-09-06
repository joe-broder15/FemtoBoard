use base64::{engine::general_purpose::URL_SAFE_NO_PAD, Engine};
use sha2::{Digest, Sha256};

/// Salted hash of a poster's IP for ban/report correlation without storing
/// the raw address. See docs/design.md §4 — salt rotates per configurable
/// interval, which is not yet wired up in this milestone.
pub fn hash_ip(ip: &str, salt: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(salt.as_bytes());
    hasher.update(b":");
    hasher.update(ip.as_bytes());
    URL_SAFE_NO_PAD.encode(hasher.finalize())
}

/// Splits `Name#password` into (display_name, tripcode). A bare name with no
/// `#` yields no tripcode. Per docs/design.md §11: a salted hash of the
/// password segment, not the legacy DES-based algorithm — no persistent
/// secret storage needed, just a fixed server-side pepper.
pub fn derive_tripcode(raw_name: &str, pepper: &str) -> (String, Option<String>) {
    match raw_name.split_once('#') {
        Some((name, secret)) if !secret.is_empty() => {
            let mut hasher = Sha256::new();
            hasher.update(pepper.as_bytes());
            hasher.update(b":");
            hasher.update(secret.as_bytes());
            let hash = URL_SAFE_NO_PAD.encode(hasher.finalize());
            let trip = format!("!{}", &hash[..10]);
            let name = if name.is_empty() {
                "Anonymous".to_string()
            } else {
                name.to_string()
            };
            (name, Some(trip))
        }
        _ => (raw_name.to_string(), None),
    }
}
