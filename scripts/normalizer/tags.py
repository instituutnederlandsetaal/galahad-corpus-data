"""Functions for making various tags valid."""

import xml.etree.ElementTree as ET

from scripts.normalizer import et_ns


def _remove_empty_i_and_b(root: ET.Element) -> None:
    """Remove `<i>` and `<b>` elements that have no text and no children."""
    # iterate so we have the parent. Need parent to remove the element if needed
    # (since .getparent() is not supported in xml.etree)
    parent_map = {c: p for p in root.iter() for c in p}
    for el in root.findall(".//tei:i", et_ns) + root.findall(".//tei:b", et_ns):
        if (el.text is None or not el.text.strip()) and len(el) == 0:
            parent = parent_map[el]
            parent.remove(el)


def _replace_hyphen_with_hyphen(root: ET.Element) -> None:
    """Replace element `<hyphen />` with actual '-'."""
    parent_map = {c: p for p in root.iter() for c in p}

    for hyphen in root.findall(".//tei:hyphen", et_ns):
        parent = parent_map.get(hyphen)
        if parent is not None:
            # insert a text node with "-" before the hyphen element
            index = list(parent).index(hyphen)
            if index == 0:
                parent.text = (parent.text or "") + "-"
            else:
                prev = parent[index - 1]
                prev.tail = (prev.tail or "") + "-"
            # remove the hyphen element
            parent.remove(hyphen)


def _remove_nolink(root: ET.Element) -> None:
    """Remove `<nolink>` elements."""
    parent_map = {c: p for p in root.iter() for c in p}
    for nolink in root.findall(".//tei:nolink", et_ns):
        parent = parent_map.get(nolink)
        if parent is not None:
            parent.remove(nolink)


def _remove_fs_in_empty_pos_w(root: ET.Element) -> None:
    """If a `<w>` has @pos="" and contains an `<fs>`, remove the `<fs>`."""
    for w in root.findall(".//tei:w", et_ns):
        if w.get("pos") is not None and not w.get("pos"):
            fs = w.find("tei:fs", et_ns)
            if fs is not None:
                w.remove(fs)


def _remove_empty_interp_grp(root: ET.Element) -> None:
    """Remove empty `<interpGrp>` elements."""
    parent_map = {c: p for p in root.iter() for c in p}
    for interp_grp in root.findall(".//tei:interpGrp", et_ns):
        if len(interp_grp) == 0 and (
            interp_grp.text is None or not interp_grp.text.strip()
        ):
            parent = parent_map.get(interp_grp)
            if parent is not None:
                parent.remove(interp_grp)


def _remove_reg_with_orig(root: ET.Element) -> None:
    """Read out the text in @orig and swap the `<reg>` with that text."""
    parent_map = {c: p for p in root.iter() for c in p}
    for reg in root.findall(".//tei:reg", et_ns):
        orig = reg.get("orig")
        if orig is not None:
            parent = parent_map.get(reg)
            if parent is not None:
                index = list(parent).index(reg)
                tail = reg.tail
                parent.remove(reg)
                if index == 0:
                    parent.text = (parent.text or "") + orig + (tail or "")
                else:
                    prev = parent[index - 1]
                    prev.tail = (prev.tail or "") + orig + (tail or "")


def remove_invalid_tags(root: ET.Element) -> None:
    """Run all tag removing functions."""
    _remove_empty_i_and_b(root)
    _replace_hyphen_with_hyphen(root)
    _remove_nolink(root)
    _remove_fs_in_empty_pos_w(root)
    _remove_empty_interp_grp(root)
    _remove_reg_with_orig(root)
