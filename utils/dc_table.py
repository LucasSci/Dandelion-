DEFAULT_DC_THRESHOLDS = (10, 15, 20, 25)
CLASSIFICATION_LABELS = ("Fracasso", "Vitória Marginal", "Sucesso", "Crítico")


def _build_thresholds_for_dc(dc: int | None) -> tuple[int, ...]:
    if dc is None:
        return DEFAULT_DC_THRESHOLDS

    base = dc
    offsets = [0] + [threshold - DEFAULT_DC_THRESHOLDS[0] for threshold in DEFAULT_DC_THRESHOLDS[1:]]
    return tuple(base + offset for offset in offsets)


def classificar_resultado(total: int, dc: int | None = None) -> str:
    thresholds = _build_thresholds_for_dc(dc)
    for label, threshold in zip(CLASSIFICATION_LABELS, thresholds):
        if total < threshold:
            return label
    return CLASSIFICATION_LABELS[-1]
