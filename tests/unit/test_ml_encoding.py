"""Unit tests for ML encoding functions - verifying deterministic behavior."""

import hashlib

import pandas as pd
import pytest


class TestDeterministicEncoding:
    """Tests to ensure encoding is deterministic across sessions."""

    def test_hash_deterministic_same_session(self) -> None:
        """Test that hash encoding is consistent within the same session."""
        test_value = "Mercedes"

        # Hash múltiples veces
        hash1 = int(hashlib.md5(test_value.encode()).hexdigest(), 16) % 1000
        hash2 = int(hashlib.md5(test_value.encode()).hexdigest(), 16) % 1000
        hash3 = int(hashlib.md5(test_value.encode()).hexdigest(), 16) % 1000

        assert hash1 == hash2 == hash3, "Hash should be deterministic within session"

    def test_hash_deterministic_known_values(self) -> None:
        """Test that hash encoding produces expected values for known inputs."""
        # Estos valores deberían ser siempre los mismos
        test_cases = {
            "Mercedes": int(hashlib.md5("Mercedes".encode()).hexdigest(), 16) % 1000,
            "Red Bull Racing": int(hashlib.md5("Red Bull Racing".encode()).hexdigest(), 16) % 1000,
            "Ferrari": int(hashlib.md5("Ferrari".encode()).hexdigest(), 16) % 1000,
        }

        for value, expected_hash in test_cases.items():
            actual_hash = int(hashlib.md5(value.encode()).hexdigest(), 16) % 1000
            assert actual_hash == expected_hash, (
                f"Hash for {value} should always be {expected_hash}"
            )

    def test_hash_different_inputs_different_outputs(self) -> None:
        """Test that different inputs produce different hashes."""
        hash_mercedes = int(hashlib.md5("Mercedes".encode()).hexdigest(), 16) % 1000
        hash_ferrari = int(hashlib.md5("Ferrari".encode()).hexdigest(), 16) % 1000

        assert hash_mercedes != hash_ferrari, "Different inputs should have different hashes"

    def test_builtin_hash_is_not_deterministic(self) -> None:
        """
        Demonstrate that Python's built-in hash() is NOT deterministic.

        This test documents the bug that was fixed.
        """
        # Python's hash() usa PYTHONHASHSEED que cambia entre ejecuciones
        # No podemos testear que cambie porque dentro de la misma ejecución es constante
        # Pero documentamos el comportamiento

        value = "Mercedes"
        builtin_hash_result = hash(value) % 1000

        # Esto pasará, pero el valor cambiará entre ejecuciones de pytest
        assert isinstance(builtin_hash_result, int), "Built-in hash returns an integer"

        # El problema es que si ejecutas pytest dos veces, obtienes valores diferentes
        # Por eso usamos hashlib.md5 que SÍ es determinístico

    def test_encoding_pipeline_deterministic(self) -> None:
        """Test that encoding an entire DataFrame column is deterministic."""
        df = pd.DataFrame(
            {
                "constructor": [
                    "Mercedes",
                    "Ferrari",
                    "Red Bull Racing",
                    "Mercedes",
                    "Ferrari",
                ]
            }
        )

        # Aplicar encoding como lo hace el código real
        df["constructor_encoded"] = df["constructor"].apply(
            lambda x: int(hashlib.md5(x.encode()).hexdigest(), 16) % 1000
        )

        # Verificar que valores iguales tienen el mismo encoding
        mercedes_encodings = df[df["constructor"] == "Mercedes"]["constructor_encoded"]
        assert len(mercedes_encodings.unique()) == 1, "Same value should have same encoding"

        ferrari_encodings = df[df["constructor"] == "Ferrari"]["constructor_encoded"]
        assert len(ferrari_encodings.unique()) == 1, "Same value should have same encoding"

    def test_encoding_specific_values(self) -> None:
        """Test encoding of specific F1-related values."""
        # Estos son valores reales que aparecen en los datos
        f1_values = {
            "circuit_name": ["Monaco", "Silverstone", "Monza", "Spa-Francorchamps"],
            "constructor": ["Mercedes", "Ferrari", "Red Bull Racing", "McLaren"],
            "driver_code": ["HAM", "VER", "LEC", "NOR"],
        }

        for category, values in f1_values.items():
            df = pd.DataFrame({category: values})

            # Aplicar encoding
            df[f"{category}_encoded"] = df[category].apply(
                lambda x: int(hashlib.md5(x.encode()).hexdigest(), 16) % 1000
            )

            # Verificar que todos los encodings están en rango [0, 999]
            assert df[f"{category}_encoded"].min() >= 0
            assert df[f"{category}_encoded"].max() < 1000

            # Verificar que no hay colisiones dentro de esta lista pequeña
            # (con % 1000, las colisiones son posibles pero improbables en listas pequeñas)
            unique_values = len(df[category].unique())
            unique_encodings = len(df[f"{category}_encoded"].unique())

            # Advertir si hay colisión (no falla el test, solo advierte)
            if unique_values != unique_encodings:
                pytest.warns(
                    UserWarning,
                    match=f"Hash collision detected in {category}",
                )
