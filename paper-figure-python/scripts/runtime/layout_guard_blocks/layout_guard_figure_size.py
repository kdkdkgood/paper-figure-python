def figure_size(cfg: dict) -> tuple[float, float]:
    width_in = mm_to_inch(float(cfg["layout_spec"]["width_mm"]))
    height_in = width_in / float(cfg["layout_spec"]["aspect_ratio"])
    return width_in, height_in
