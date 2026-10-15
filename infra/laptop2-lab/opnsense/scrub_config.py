"""Remove secrets from an OPNsense configuration backup before committing it.

Usage: python scrub_config.py config-YYYY-MM-DD.xml [config-scrubbed.xml]

The raw backup stays local (ignored by git); only the scrubbed copy is committed.
"""
import re
import sys

# Fields that hold password hashes, private keys, certificates or API secrets.
SECRET_TAGS = [
    "password", "bcrypt-hash", "prv", "crt", "csr", "key", "secret",
    "apikeys", "authorizedkeys", "otp_seed", "psk", "pre-shared-key",
    "privkey", "privatekey", "tunable_secret",
]


def scrub(text):
    count = 0
    for tag in SECRET_TAGS:
        pattern = re.compile(rf"<{re.escape(tag)}>(.+?)</{re.escape(tag)}>", re.DOTALL)
        text, n = pattern.subn(f"<{tag}>REDACTED</{tag}>", text)
        count += n
    return text, count


def main():
    src = sys.argv[1]
    dst = sys.argv[2] if len(sys.argv) > 2 else "config-scrubbed.xml"
    with open(src, encoding="utf-8") as f:
        text = f.read()
    text, count = scrub(text)
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"{count} secret fields redacted, written to {dst}")


if __name__ == "__main__":
    main()
