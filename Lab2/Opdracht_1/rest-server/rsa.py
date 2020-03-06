from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA512, SHA384, SHA256, SHA, MD5
from Crypto import Random
from base64 import b64encode, b64decode

use_hash = "SHA-256"

def _get_digest():
    _hashes = {
        "SHA-1"  : SHA.new,
        "SHA-256": SHA256.new,
        "SHA-384": SHA384.new,
        "SHA-512": SHA512.new,
        "MD5"    : MD5.new,
    }

    return _hashes.get(use_hash, _hashes["MD5"])()

def newkeys(keysize):
    random_generator = Random.new().read
    key = RSA.generate(keysize, random_generator)
    private, public = key, key.publickey()
    return public, private

def importKey(externKey):
    return RSA.importKey(externKey)

def getpublickey(priv_key):
    return priv_key.publickey()

def encrypt(message, pub_key):
    #RSA encryption protocol according to PKCS#1 OAEP
    cipher = PKCS1_OAEP.new(pub_key)
    return cipher.encrypt(message)

def decrypt(ciphertext, priv_key):
    #RSA encryption protocol according to PKCS#1 OAEP
    cipher = PKCS1_OAEP.new(priv_key)
    return cipher.decrypt(ciphertext)

def sign(message, priv_key, hashAlg="SHA-256"):
    global use_hash
    use_hash = hashAlg
    signer = PKCS1_v1_5.new(priv_key)
    digest = _get_digest()
    digest.update(message)
    return signer.sign(digest)

def verify(message, signature, pub_key):
    signer = PKCS1_v1_5.new(pub_key)
    digest = _get_digest()
    digest.update(message)
    return signer.verify(digest, signature)
