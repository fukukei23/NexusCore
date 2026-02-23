from sandbox_output.sample import is_prime


def test_primes():
    assert is_prime(2) is True  # ここで失敗するはず
    assert is_prime(3) is True
    assert is_prime(4) is False
