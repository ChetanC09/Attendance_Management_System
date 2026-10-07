from app.core.security import hash_password, verify_password


def test_password_hash_uses_argon2_and_verifies_only_matching_password() -> None:
    encoded = hash_password("Correct horse battery staple 42!")
    assert encoded.startswith("$argon2id$")
    assert verify_password("Correct horse battery staple 42!", encoded)
    assert not verify_password("not the password", encoded)
