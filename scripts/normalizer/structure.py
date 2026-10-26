"""Functions for fixing structural issues in the TEI files."""

import xml.etree.ElementTree as ET

from scripts.normalizer import et_ns, ns


def _move_cit_to_text_body(root: ET.Element) -> None:
    """
    Move `<cit>` to `<text> <body> <cit> </text> </body>`.

    Raises:
        ValueError: TEI structure not supported.
    """
    children = list(root)
    if len(children) != 2:
        raise ValueError("Unexpected structure")
    if children[0].tag != f"{ns['tei']}teiHeader":
        raise ValueError("First child is not <teiHeader>")
    if children[1].tag == f"{ns['tei']}text":
        return
    if children[1].tag != f"{ns['tei']}cit":
        raise ValueError(f"Second child is neither <text> nor <cit>: {children[1].tag}")

    # wrap the <cit> into <text><body>...</body></text>
    cit = root.find(".//tei:cit", et_ns)
    if cit is None:
        raise ValueError("No <cit> found")
    # remove cit from root
    root.remove(cit)
    # create new elements
    text_elem = ET.Element(f"{ns['tei']}text")
    body_elem = ET.Element(f"{ns['tei']}body")
    # move cit into body, and body into text
    body_elem.append(cit)
    text_elem.append(body_elem)
    # append text to root
    root.append(text_elem)


def _put_p_in_div(root: ET.Element) -> None:
    """
    `<div>`'s may not contain both `<div>`'s and `<p>`'s.
    Move these `<p>` into a `<div>` inside the parent `<div>`.
    """
    for div in root.findall(".//tei:div", et_ns):
        for p in div.findall("tei:p", et_ns):
            if p is not None and len(div.findall("tei:div", et_ns)) > 0:
                # create a new <div> and move the <p> into it
                child_div = ET.Element(f"{ns['tei']}div")
                child_div.append(p)
                div.append(child_div)
                # remove the original <p> from div
                div.remove(p)


def _fix_date_and_inter_grp_in_cit(root: ET.Element) -> None:
    """Turn <cit> <date> </cit> into <cit> <note> <date> <note/> <cit/>."""
    for cit in root.findall(".//tei:cit", et_ns):
        date = cit.find("tei:date", et_ns)

        if date is None:
            continue

        note = ET.Element(f"{ns['tei']}note")
        ab = ET.SubElement(note, f"{ns['tei']}ab")
        ab.append(date)
        cit.insert(0, note)
        # remove date from its original position
        cit.remove(date)
        # move @timeSpan to @extent
        if "timeSpan" in date.attrib:
            date.set("extent", date.get("timeSpan"))
            del date.attrib["timeSpan"]

        # next, add a interpGrp and interp for each attribute of cit
        for attr in ["lemma", "pos", "sense-id", "modern-lemma", "entry-id"]:
            if attr in cit.attrib:
                _attr_to_interp(cit, attr, ab)

        # remove partition
        del cit.attrib["partition"]
        # cit contains at q with at least one <w> with @sense-id, move it to @lemmaRef
        q = cit.find("tei:q", et_ns)
        for w in q.findall(".//tei:w", et_ns):
            if "sense-id" in w.attrib:
                w.set("lemmaRef", w.get("sense-id"))
                del w.attrib["sense-id"]


def _attr_to_interp(cit: ET.Element, attr: str, ab: ET.Element) -> None:
    """Move an attribute of cit to an interp in an interpGrp in the `<ab>`."""
    interp_grp = ET.SubElement(ab, f"{ns['tei']}interpGrp", type=attr)
    interp = ET.SubElement(interp_grp, f"{ns['tei']}interp")
    interp.text = cit.get(attr)
    del cit.attrib[attr]


def _create_interp_grp_for_dictionary_xr(root: ET.Element) -> None:
    """Transform custom dictionary tags to a structured `<interpGrp>`."""
    # transform:
    # <xr>
    # <ref citaatId="13531">
    #     <modern_lemma>ook</modern_lemma>
    #     <lemma>ooc</lemma>
    #     <def>ook; ook wel</def>
    #     <pos>bw.</pos>
    # </ref>
    # </xr>
    # into:
    # <xr>
    # <ref>
    #     <interpGrp>
    #         <interp type="citaatId">13531</interp>
    #         <interp type="modern_lemma">ook</interp>
    #         <interp type="lemma">ooc</interp>
    #         <interp type="def">ook; ook wel</interp>
    #         <interp type="pos">bw.</interp>
    #     </interpGrp>
    # </ref>
    # </xr>
    for xr in root.findall(".//tei:xr", et_ns):
        for ref in xr.findall("tei:ref", et_ns):
            interp_grp = ET.SubElement(ref, f"{ns['tei']}interpGrp")

            for child in list(ref):
                if child.tag in {
                    f"{ns['tei']}modern_lemma",
                    f"{ns['tei']}lemma",
                    f"{ns['tei']}def",
                    f"{ns['tei']}pos",
                }:
                    interp = ET.SubElement(
                        interp_grp,
                        f"{ns['tei']}interp",
                        type=child.tag[len(ns["tei"]) :],
                    )
                    interp.text = child.text
                    ref.remove(child)

            cit_id = ref.get("citaatId")
            if cit_id is not None:
                interp = ET.SubElement(
                    interp_grp,
                    f"{ns['tei']}interp",
                    type="citaatId",
                )
                interp.text = cit_id
                del ref.attrib["citaatId"]


def _remove_s_containing_l(root: ET.Element) -> None:
    """Remove `<s>` elements containing `<l>` elements. The `<l>` elements should become children of the parent of `<s>`."""
    parent_map = {c: p for p in root.iter() for c in p}
    for s in root.findall(".//tei:s", et_ns):
        l = s.find("tei:l", et_ns)
        if l is not None:
            parent = parent_map.get(s)
            idx = list(parent).index(s)
            for child in list(s):
                parent.insert(idx, child)
                idx += 1
            parent.remove(s)


def fix_structural_issues(root: ET.Element) -> None:
    """Fix structural issues in the TEI document."""
    _move_cit_to_text_body(root)
    _put_p_in_div(root)
    _fix_date_and_inter_grp_in_cit(root)
    _create_interp_grp_for_dictionary_xr(root)
    _remove_s_containing_l(root)
