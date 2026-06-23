def _collect_panel_group_bboxes_px(fig: plt.Figure, axes_grid) -> dict[tuple[int, int], np.ndarray]:
    if axes_grid is None:
        return {}
    try:
        renderer = fig.canvas.get_renderer()
    except Exception:
        return {}

    def _to_bbox_array(bbox) -> np.ndarray | None:
        if bbox is None:
            return None
        vals = (bbox.x0, bbox.y0, bbox.x1, bbox.y1)
        if not all(np.isfinite(v) for v in vals):
            return None
        if bbox.width <= 0 or bbox.height <= 0:
            return None
        return np.array([float(bbox.x0), float(bbox.y0), float(bbox.x1), float(bbox.y1)], dtype=float)

    def _merge_bbox(base: np.ndarray | None, add: np.ndarray | None) -> np.ndarray | None:
        if add is None:
            return base
        if base is None:
            return np.array(add, dtype=float)
        return np.array(
            [
                min(float(base[0]), float(add[0])),
                min(float(base[1]), float(add[1])),
                max(float(base[2]), float(add[2])),
                max(float(base[3]), float(add[3])),
            ],
            dtype=float,
        )

    def _artist_bbox_array(artist) -> np.ndarray | None:
        if artist is None:
            return None
        try:
            if hasattr(artist, "get_visible") and (not artist.get_visible()):
                return None
            bbox = artist.get_window_extent(renderer)
        except Exception:
            return None
        return _to_bbox_array(bbox)

    index_by_axes_id: dict[int, tuple[int, int]] = {}
    panel_bboxes: dict[tuple[int, int], np.ndarray] = {}

    nrows, ncols = axes_grid.shape
    for row_idx in range(nrows):
        for col_idx in range(ncols):
            ax = axes_grid[row_idx, col_idx]
            if ax is None or not ax.get_visible():
                continue
            index_by_axes_id[id(ax)] = (row_idx, col_idx)
            panel_bbox: np.ndarray | None = None
            consumed_artist_ids: set[int] = set()
            try:
                panel_bbox = _merge_bbox(panel_bbox, _to_bbox_array(ax.get_tightbbox(renderer)))
            except Exception:
                pass

            # 显式并入“子图归属元素”：图例、编号、标注等文字 artist。
            legend_artist = ax.get_legend()
            if legend_artist is not None:
                consumed_artist_ids.add(id(legend_artist))
            panel_bbox = _merge_bbox(panel_bbox, _artist_bbox_array(legend_artist))
            for text_artist in list(ax.texts):
                consumed_artist_ids.add(id(text_artist))
                panel_bbox = _merge_bbox(panel_bbox, _artist_bbox_array(text_artist))
            try:
                extra_artists = list(ax.get_default_bbox_extra_artists())
            except Exception:
                extra_artists = []
            for artist in extra_artists:
                if artist is None:
                    continue
                artist_id = id(artist)
                if artist_id in consumed_artist_ids:
                    continue
                consumed_artist_ids.add(artist_id)
                panel_bbox = _merge_bbox(panel_bbox, _artist_bbox_array(artist))

            if panel_bbox is not None:
                panel_bboxes[(row_idx, col_idx)] = panel_bbox

    # 将 colorbar 轴并入其所属主轴边界，确保热力图/等高线/hexbin 被作为整体子图看待。
    for ax in fig.axes:
        if ax is None or not ax.get_visible():
            continue
        if id(ax) in index_by_axes_id:
            continue

        parent_idx: tuple[int, int] | None = None

        # Path 1: _colorbar 私有属性（matplotlib >= 3.5）
        cb_obj = getattr(ax, "_colorbar", None)
        if cb_obj is not None:
            mappable = getattr(cb_obj, "mappable", None)
            parent_ax = getattr(mappable, "axes", None)
            parent_idx = index_by_axes_id.get(id(parent_ax))

        # Path 2: 从网格轴的 images/collections 反向查找
        if parent_idx is None:
            for gax in fig.axes:
                gax_idx = index_by_axes_id.get(id(gax))
                if gax_idx is None:
                    continue
                for artist_list in (getattr(gax, "images", []), getattr(gax, "collections", [])):
                    for artist in artist_list:
                        cb = getattr(artist, "colorbar", None)
                        if cb is not None and getattr(cb, "ax", None) is ax:
                            parent_idx = gax_idx
                            break
                    if parent_idx is not None:
                        break
                if parent_idx is not None:
                    break

        if parent_idx is None:
            continue
        try:
            add_bbox = _to_bbox_array(ax.get_tightbbox(renderer))
        except Exception:
            add_bbox = None
        if add_bbox is None:
            continue
        panel_bboxes[parent_idx] = _merge_bbox(panel_bboxes.get(parent_idx), add_bbox)

    return panel_bboxes
