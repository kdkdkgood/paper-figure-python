def _collect_figure_bbox_px(fig: plt.Figure) -> np.ndarray | None:
    try:
        renderer = fig.canvas.get_renderer()
    except Exception:
        return None
    x0 = np.inf
    y0 = np.inf
    x1 = -np.inf
    y1 = -np.inf
    found = False

    def _consume_bbox(bbox) -> None:
        nonlocal x0, y0, x1, y1, found
        if bbox is None:
            return
        vals = (bbox.x0, bbox.y0, bbox.x1, bbox.y1)
        if not all(np.isfinite(v) for v in vals):
            return
        if bbox.width <= 0 or bbox.height <= 0:
            return
        x0 = min(x0, float(bbox.x0))
        y0 = min(y0, float(bbox.y0))
        x1 = max(x1, float(bbox.x1))
        y1 = max(y1, float(bbox.y1))
        found = True

    for ax in fig.axes:
        if not ax.get_visible():
            continue
        try:
            _consume_bbox(ax.get_tightbbox(renderer))
        except Exception:
            continue

    for legend in fig.legends:
        if legend is None or not legend.get_visible():
            continue
        try:
            _consume_bbox(legend.get_window_extent(renderer))
        except Exception:
            continue

    # 显式并入 figure 级文本（如 suptitle/fig.text），避免全局边界漏算。
    for text in getattr(fig, "texts", []):
        if text is None:
            continue
        try:
            if not text.get_visible():
                continue
            _consume_bbox(text.get_window_extent(renderer))
        except Exception:
            continue

    # 并入 figure 级默认 extra artists（如 suptitle/额外注释容器），避免全图漏算。
    try:
        extra_artists = list(fig.get_default_bbox_extra_artists())
    except Exception:
        extra_artists = []
    consumed_ids = {id(item) for item in getattr(fig, "texts", []) if item is not None}
    consumed_ids.update(id(item) for item in fig.legends if item is not None)
    for artist in extra_artists:
        if artist is None:
            continue
        artist_id = id(artist)
        if artist_id in consumed_ids:
            continue
        consumed_ids.add(artist_id)
        try:
            if hasattr(artist, "get_visible") and (not artist.get_visible()):
                continue
            _consume_bbox(artist.get_window_extent(renderer))
        except Exception:
            continue

    if not found:
        return None
    return np.array([x0, y0, x1, y1], dtype=float)
