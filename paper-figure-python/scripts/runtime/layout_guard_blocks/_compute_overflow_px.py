def _compute_overflow_px(bbox: np.ndarray, fig_w_px: float, fig_h_px: float, pad_px: float) -> dict[str, float]:
    return {
        "left": max(0.0, pad_px - float(bbox[0])),
        "bottom": max(0.0, pad_px - float(bbox[1])),
        "right": max(0.0, float(bbox[2]) - (fig_w_px - pad_px)),
        "top": max(0.0, float(bbox[3]) - (fig_h_px - pad_px)),
    }
