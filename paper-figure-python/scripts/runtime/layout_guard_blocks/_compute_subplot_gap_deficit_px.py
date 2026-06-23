def _compute_subplot_gap_deficit_px(
    panel_bboxes: dict[tuple[int, int], np.ndarray],
    *,
    nrows: int,
    ncols: int,
    min_hgap_px: float,
    min_vgap_px: float,
    tolerance_px: float,
) -> dict[str, float]:
    h_deficit_px = 0.0
    v_deficit_px = 0.0
    h_excess_px = 0.0
    v_excess_px = 0.0

    if ncols > 1:
        for row_idx in range(nrows):
            for col_idx in range(ncols - 1):
                left_bbox = panel_bboxes.get((row_idx, col_idx))
                right_bbox = panel_bboxes.get((row_idx, col_idx + 1))
                if left_bbox is None or right_bbox is None:
                    continue
                gap_px = float(right_bbox[0]) - float(left_bbox[2])
                need_px = float(min_hgap_px) - gap_px
                if need_px > float(tolerance_px):
                    h_deficit_px = max(h_deficit_px, need_px)
                extra_px = gap_px - float(min_hgap_px)
                if extra_px > float(tolerance_px):
                    h_excess_px = max(h_excess_px, extra_px)

    if nrows > 1:
        for row_idx in range(nrows - 1):
            for col_idx in range(ncols):
                upper_bbox = panel_bboxes.get((row_idx, col_idx))
                lower_bbox = panel_bboxes.get((row_idx + 1, col_idx))
                if upper_bbox is None or lower_bbox is None:
                    continue
                gap_px = float(upper_bbox[1]) - float(lower_bbox[3])
                need_px = float(min_vgap_px) - gap_px
                if need_px > float(tolerance_px):
                    v_deficit_px = max(v_deficit_px, need_px)
                extra_px = gap_px - float(min_vgap_px)
                if extra_px > float(tolerance_px):
                    v_excess_px = max(v_excess_px, extra_px)

    return {
        "horizontal": float(max(0.0, h_deficit_px)),
        "vertical": float(max(0.0, v_deficit_px)),
        "horizontal_excess": float(max(0.0, h_excess_px)),
        "vertical_excess": float(max(0.0, v_excess_px)),
    }
