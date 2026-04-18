from researchflow.context.renderers.xml import to_xml

_RENDERERS = {"xml": to_xml}


def get_renderer(name: str):
    if name not in _RENDERERS:
        raise KeyError(f"Unknown renderer '{name}'. Registered: {sorted(_RENDERERS)}")
    return _RENDERERS[name]


__all__ = ["get_renderer", "to_xml"]
