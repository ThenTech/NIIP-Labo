import rsa
from base64 import b64encode, b64decode
from Crypto.PublicKey import RSA

# msg1 = "Hello Tony, I am Jarvis!"
# msg2 = "Hello Toni, I am Jarvis!"
# keysize = 2048
# (public, private) = rsa.newkeys(keysize)
# encrypted = b64encode(rsa.encrypt(msg1, public))
# decrypted = rsa.decrypt(b64decode(encrypted), private)
# signature = b64encode(rsa.sign(msg1, private, "SHA-512"))
# verify = rsa.verify(msg1, b64decode(signature), public)

# print(private.exportKey('PEM'))
# print(public.exportKey('PEM'))
# print("Encrypted: " + encrypted)
# print("Decrypted: '%s'" % decrypted)
# print("Signature: " + signature)
# print("Verify: %s" % verify)
# rsa.verify(msg2, b64decode(signature), public)

f = open('cert/private.pem','r')
r = RSA.importKey(f.read(),  passphrase='printeronfire')

sign = b64encode(rsa.sign("M2M3MWJmODc3YzI0_niip", r))

# obj = {
#     "temperature": 50
# }

# publicKey = RSA.importKey(open("cert/public.pem", "rb"))
# cipher = "SUcV1na04ZHXruX9QZenN3aYbNM2foAZCskeD6Kwv3t1tZuGDslFBvsr6i7HP+CiZspBdDEPKsLzpnrSvzfFJ/DBb6sf/JKMMs8h/tpdaB9aXFTCHFmyRQ3stsXlMmQFi1kTIN+L38AFvzASAp1oVT/divuFMEiRDhQu7jKOqA0jc76ru6TtcKWnYNPIRSYx7kJ2NlRKGFYIdPEnUVuCmXnpeuS28ub0giMqBH0UEkRaJXCF+XkUwPuX4sAI8rqwL6KsJjDF9wyfpB/WKN51At+fHPVLNJOO2+oR/y3P8kH7Y+gcb0rx9FfxtvnToSiPVclTbyrr5f+N0eia0s9CRQ=="



cipher = "LncSNPnL/uueCxMjfhzfwgiNmAoqF05WOEfunqOtricONYTGzWxyF1gzIzKEsiRh1KzhLyjayGF/K2DONC+HDZbPMRIDYQBqhdzH37a+y7h2laDm6DYW3V/bEqM5bwcD3p2Kmi6d4RuxD24dHW7TB7JhN2O+I6EyFRsTLrfifFtKlbw26hD3sxlGOtitpMJgzd7DEjKNglXpJRUhPvwFtIIwkLP7E07+tvykLMgTd+8fBzwxKtW1GmhzzseJbjlSawGWb3WxePpVz1ahi7eZ5rLPDa439A2VMCow3ybdZ1ibU13J19Q7YC6NXLlk2Yp+CeK0XRS3pFUnbXeXoC1OXw=="
val = rsa.decrypt(b64decode(cipher), r)

print val