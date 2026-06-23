def clamp_adjust_spec(adjust: dict, guard_spec: dict) -> dict:
    left = float(adjust["left"])
    right = float(adjust["right"])
    top = float(adjust["top"])
    bottom = float(adjust["bottom"])
    min_inner_w = float(guard_spec["min_inner_width_frac"])
    min_inner_h = float(guard_spec["min_inner_height_frac"])

    left = min(0.98, max(0.0, left))
    right = min(1.0, max(left + 1e-6, right))
    bottom = min(0.98, max(0.0, bottom))
    top = min(1.0, max(bottom + 1e-6, top))

    span_x = right - left
    if span_x < min_inner_w:
        deficit = min_inner_w - span_x
        left = max(0.0, left - deficit / 2.0)
        right = min(1.0, right + deficit / 2.0)
        if (right - left) < min_inner_w:
            if left <= 0.0:
                right = min(1.0, left + min_inner_w)
            if right >= 1.0:
                left = max(0.0, right - min_inner_w)

    span_y = top - bottom
    if span_y < min_inner_h:
        deficit = min_inner_h - span_y
        bottom = max(0.0, bottom - deficit / 2.0)
        top = min(1.0, top + deficit / 2.0)
        if (top - bottom) < min_inner_h:
            if bottom <= 0.0:
                top = min(1.0, bottom + min_inner_h)
            if top >= 1.0:
                bottom = max(0.0, top - min_inner_h)

    adjust["left"] = float(left)
    adjust["right"] = float(right)
    adjust["top"] = float(top)
    adjust["bottom"] = float(bottom)
    if "wspace" in adjust:
        adjust["wspace"] = float(adjust["wspace"])
    if "hspace" in adjust:
        adjust["hspace"] = float(adjust["hspace"])
    return adjust
