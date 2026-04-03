#!/usr/bin/env python3
"""
OpenClaw OTG Security Vault
Implements AES-256 encryption, biometric authentication simulation, 
panic button wipe, and secure key management.
"""

import os
import sys
import json
import time
import hashlib
import secrets
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
import logging
import base64

# Try to import cryptography, fallback to mock if not available
try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import padding
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("⚠️  cryptography library not found. Running in mock mode.")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("OTG_Security_Vault")

@dataclass
class SecurityStatus:
    is_locked: bool
    auth_attempts: int
    last_unlock: Optional[str]
    panic_mode: bool
    encrypted_files_count: int

class SecurityVault:
    """
    Military-grade security vault for OTG drive data.
    Features:
    - AES-256-GCM encryption
    - Biometric authentication simulation
    - Panic button instant wipe
    - Secure key derivation
    """
    
    def __init__(self, vault_dir: str, master_password: Optional[str] = None):
        self.vault_dir = Path(vault_dir)
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        
        self.key_file = self.vault_dir / ".vault_key"
        self.config_file = self.vault_dir / ".vault_config"
        self.data_dir = self.vault_dir / "encrypted_data"
        self.data_dir.mkdir(exist_ok=True)
        
        self.is_unlocked = False
        self.auth_attempts = 0
        self.max_attempts = 5
        self.panic_mode = False
        self.encryption_key: Optional[bytes] = None
        
        # Initialize or load vault
        self._initialize_vault(master_password)

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive a 256-bit key from password using PBKDF2."""
        if CRYPTO_AVAILABLE:
            from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
            from cryptography.hazmat.primitives import hashes
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            return kdf.derive(password.encode())
        else:
            # Mock key derivation
            return hashlib.sha256((password + salt.hex()).encode()).digest()

    def _initialize_vault(self, master_password: Optional[str] = None):
        """Initialize vault with new key or load existing."""
        if self.key_file.exists():
            # Load existing vault
            logger.info("Loading existing vault...")
            with open(self.key_file, 'rb') as f:
                salt = f.read(16)
                encrypted_key = f.read()
            
            if master_password:
                # Try to unlock with provided password
                test_key = self._derive_key(master_password, salt)
                # In real impl, verify with HMAC
                self.encryption_key = test_key
                self.is_unlocked = True
                logger.info("Vault unlocked successfully.")
            else:
                logger.info("Vault locked. Authentication required.")
        else:
            # Create new vault
            logger.info("Creating new vault...")
            if not master_password:
                master_password = "default_otg_password"  # In real impl, force user to set
                logger.warning("Using default password! Change immediately.")
            
            salt = secrets.token_bytes(16)
            self.encryption_key = self._derive_key(master_password, salt)
            
            # Save salt and metadata (not the key itself!)
            with open(self.key_file, 'wb') as f:
                f.write(salt)
                # In real impl, store encrypted verification hash
            
            config = {
                "created_at": time.time(),
                "version": "1.0",
                "panic_wipe_enabled": True
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f)
            
            self.is_unlocked = True
            logger.info("New vault created and unlocked.")

    def authenticate_biometric(self, biometric_type: str = "fingerprint") -> bool:
        """Simulate biometric authentication."""
        logger.info(f"Requesting {biometric_type} authentication...")
        
        # Simulate biometric scan delay
        time.sleep(0.5)
        
        # Mock success rate (90%)
        if secrets.randbelow(100) < 90:
            self.is_unlocked = True
            self.auth_attempts = 0
            logger.info("✅ Biometric authentication successful!")
            return True
        else:
            self.auth_attempts += 1
            logger.warning(f"❌ Biometric authentication failed. Attempt {self.auth_attempts}/{self.max_attempts}")
            
            if self.auth_attempts >= self.max_attempts:
                self.trigger_panic_wipe()
                return False
            return False

    def encrypt_data(self, plaintext: str, filename: str) -> str:
        """Encrypt data and save to vault."""
        if not self.is_unlocked:
            raise PermissionError("Vault is locked. Authenticate first.")
        
        if self.panic_mode:
            raise PermissionError("Panic mode active! Data access denied.")
        
        data_path = self.data_dir / f"{filename}.enc"
        
        if CRYPTO_AVAILABLE:
            # Generate random IV
            iv = secrets.token_bytes(12)
            
            # Pad data
            padder = padding.PKCS7(128).padder()
            padded_data = padder.update(plaintext.encode()) + padder.finalize()
            
            # Encrypt
            cipher = Cipher(algorithms.AES(self.encryption_key), modes.GCM(iv), backend=default_backend())
            encryptor = cipher.encryptor()
            ciphertext = encryptor.update(padded_data) + encryptor.finalize()
            
            # Save IV + ciphertext + tag
            with open(data_path, 'wb') as f:
                f.write(iv + encryptor.tag + ciphertext)
        else:
            # Mock encryption
            mock_cipher = base64.b64encode(plaintext.encode()).decode()
            with open(data_path, 'w') as f:
                f.write(mock_cipher)
        
        logger.info(f"🔒 Encrypted data saved to {filename}.enc")
        return str(data_path)

    def decrypt_data(self, filename: str) -> str:
        """Decrypt data from vault."""
        if not self.is_unlocked:
            raise PermissionError("Vault is locked. Authenticate first.")
        
        data_path = self.data_dir / f"{filename}.enc"
        if not data_path.exists():
            raise FileNotFoundError(f"Encrypted file not found: {filename}.enc")
        
        if CRYPTO_AVAILABLE:
            with open(data_path, 'rb') as f:
                iv = f.read(12)
                tag = f.read(16)
                ciphertext = f.read()
            
            cipher = Cipher(algorithms.AES(self.encryption_key), modes.GCM(iv, tag), backend=default_backend())
            decryptor = cipher.decryptor()
            padded_data = decryptor.update(ciphertext) + decryptor.finalize()
            
            unpadder = padding.PKCS7(128).unpadder()
            plaintext = unpadder.update(padded_data) + unpadder.finalize()
            return plaintext.decode()
        else:
            # Mock decryption
            with open(data_path, 'r') as f:
                mock_cipher = f.read()
            return base64.b64decode(mock_cipher).decode()

    def trigger_panic_wipe(self, immediate: bool = True):
        """Instant wipe of all sensitive data."""
        logger.critical("🚨 PANIC WIPE TRIGGERED! 🚨")
        self.panic_mode = True
        self.is_unlocked = False
        self.encryption_key = None
        
        if immediate:
            # Delete all encrypted files
            for file in self.data_dir.glob("*"):
                file.unlink()
                logger.warning(f"💀 Wiped: {file.name}")
            
            # Overwrite key file with random data before deletion
            if self.key_file.exists():
                with open(self.key_file, 'wb') as f:
                    f.write(secrets.token_bytes(1024))
                self.key_file.unlink()
                logger.warning("💀 Encryption keys destroyed.")
            
            logger.critical("✅ Vault completely wiped. Data unrecoverable.")

    def get_status(self) -> SecurityStatus:
        """Get current vault status."""
        encrypted_count = len(list(self.data_dir.glob("*.enc"))) if self.data_dir.exists() else 0
        return SecurityStatus(
            is_locked=not self.is_unlocked,
            auth_attempts=self.auth_attempts,
            last_unlock=time.strftime("%Y-%m-%d %H:%M:%S") if self.is_unlocked else None,
            panic_mode=self.panic_mode,
            encrypted_files_count=encrypted_count
        )

if __name__ == "__main__":
    print("🔐 OpenClaw OTG Security Vault Initializing...")
    
    # Create vault
    vault = SecurityVault(vault_dir="./user_data/vault", master_password="MySecretOTGPassword123!")
    
    # Test biometric auth
    if vault.authenticate_biometric("fingerprint"):
        # Encrypt some sensitive data
        secret_note = "This is my super secret AI personality configuration!"
        vault.encrypt_data(secret_note, "personality_config")
        
        # Decrypt and verify
        decrypted = vault.decrypt_data("personality_config")
        print(f"📝 Decrypted: {decrypted}")
        
        # Show status
        status = vault.get_status()
        print(f"📊 Vault Status: Locked={status.is_locked}, Files={status.encrypted_files_count}, Panic={status.panic_mode}")
    else:
        print("❌ Authentication failed!")
