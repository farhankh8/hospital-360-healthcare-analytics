"""HOSPITAL 360 synthetic data generator package."""


def __getattr__(name: str):
    """Expose ``generate_all`` lazily (keeps ``python -m generator.generate`` clean)."""
    if name == "generate_all":
        from .generate import generate_all
        return generate_all
    raise AttributeError(name)


__all__ = ["generate_all"]
