from werkzeug.security import generate_password_hash
print(generate_password_hash('tu_contraseña'))
# Copiar el hash al .env