# test_decouple.py
from decouple import config

EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT', cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', cast=bool)

print(f"EMAIL_HOST: {EMAIL_HOST}")
print(f"EMAIL_PORT: {EMAIL_PORT}")
print(f"EMAIL_HOST_USER: {EMAIL_HOST_USER}")
print(f"EMAIL_HOST_PASSWORD: {EMAIL_HOST_PASSWORD}")
print(f"EMAIL_USE_TLS: {EMAIL_USE_TLS}")
