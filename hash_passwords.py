import bcrypt

passwords = ['test123', 'sumac123', 'smep456']

hashed_passwords = [
    bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()
    for p in passwords
]

for h in hashed_passwords:
    print(h)
