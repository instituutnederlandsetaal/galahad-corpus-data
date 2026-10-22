"""Function for introducting `<note>`'s to ignore redactional comments and more."""

import xml.etree.ElementTree as ET

from scripts.normalizer import et_ns, ns


def _normalize_div_type_notes(root: ET.Element) -> None:
    # Normalize <div> elements with @type="notes" to simply <note>
    for div in root.findall(".//tei:div[@type='notes']", et_ns):
        div.tag = f"{ns['tei']}note"
        if "type" in div.attrib:
            del div.attrib["type"]


def _note_redactional_comments(root: ET.Element) -> None:
    """Use None for PC, False for empty lemma and True for full lemma."""
    tags = {"q", "p", "l", "s", "add", "name"}
    # Filter out sentences that are already inside a <note>
    parent_map = {c: p for p in root.iter() for c in p}

    def not_in_note(elem: ET.Element) -> bool:
        parent = elem
        while parent is not None:
            if parent.tag == f"{ns['tei']}note":
                return False
            parent = parent_map.get(parent)
        return True

    sentences = []
    for tag in tags:
        sentences.extend(
            [
                elem
                for elem in root.findall(f".//tei:{tag}", et_ns)
                if not_in_note(elem)
            ],
        )

    for sentence in sentences:
        changed = True
        start_from = 0
        while changed:
            changed = False
            lemmas: list[bool | None] = []
            children = list(sentence)
            for w_or_pc in children:
                if w_or_pc.tag == f"{ns['tei']}pc":
                    lemmas.append(None)
                elif w_or_pc.tag == f"{ns['tei']}w":
                    if not w_or_pc.get("lemma").strip():
                        lemmas.append(False)
                    else:
                        lemmas.append(True)
                else:  # could be any other tag
                    lemmas.append(True)

            try:
                # get False with lowest id
                first_idx = lemmas.index(False, start_from)
                last_idx = first_idx

                # Expand selection backwards as long as we add <PC> (None)
                while first_idx > 0 and lemmas[first_idx - 1] is None:
                    first_idx -= 1

                # Expand forwards as long as we add empty <w> (False) or <PC> (None)
                while (
                    last_idx < len(lemmas) - 1
                    and (
                        lemmas[last_idx + 1] is not True
                        or (
                            last_idx < len(lemmas) - 2
                            and lemmas[last_idx] is False
                            and lemmas[last_idx + 1] is True
                            and lemmas[last_idx + 2] is not True
                        )  # we can jump over a single lemma, if thereafter comes an empty <w> or <pc> and before comes an empty <w>
                    )
                ):
                    last_idx += 1

                selected = children[first_idx : last_idx + 1]
                if len(selected) <= 2:  # not long enough.
                    # only go through with it if it is the last word in the sentence
                    # tends to be "enz.,"
                    if last_idx == len(children) - 1:
                        pass  # go ahead
                    else:
                        start_from = last_idx + 1
                        changed = True
                        continue

                note = ET.Element(f"{ns['tei']}note", attrib={"type": "editorial"})
                sentence.insert(first_idx, note)
                for elem in selected:
                    sentence.remove(elem)
                    note.append(elem)
                changed = True
            except:
                pass


def _put_last_enz_in_note(root: ET.Element) -> None:
    """If the last <w> of the doc has text 'enz', put it into a <note>."""
    qs = root.findall(".//tei:q", et_ns)
    for q in qs:
        w_elements = q.findall("tei:w", et_ns)
        if not w_elements:
            return
        last_w = w_elements[-1]
        text = "".join(last_w.itertext()).strip()
        if text.lower() in {"enz.", "enz", "enz.,"}:
            children = list(q)
            idx = children.index(last_w)
            # create a <note> element and move last_w into it
            note = ET.Element(f"{ns['tei']}note", attrib={"type": "editorial"})
            # add the w
            q.insert(idx, note)
            q.remove(last_w)
            note.append(last_w)


def _put_pos_999_in_note(root: ET.Element) -> None:
    parent_map = {c: p for p in root.iter() for c in p}
    for w in root.findall(".//tei:w", et_ns):
        if w.get("type") == "999" and not w.get("pos"):
            parent = parent_map.get(w)
            if parent is not None and parent.tag != f"{ns['tei']}note":
                note = ET.Element(f"{ns['tei']}note", attrib={"type": "editorial"})
                parent.insert(list(parent).index(w), note)
                parent.remove(w)
                note.append(w)


def _move_xr_to_cit_in_note(root: ET.Element) -> None:
    # transform <w> <xr> ... </xr> </w>
    # to <w> <note> <cit> <xr> </xr> </cit> </note> </w>
    for w in root.findall(".//tei:w", et_ns):
        xr = w.find("tei:xr", et_ns)
        if xr is not None:
            note = ET.SubElement(w, f"{ns['tei']}note")
            cit = ET.SubElement(note, f"{ns['tei']}cit")
            cit.append(xr)
            w.remove(xr)



def _put_RM_in_note(root: ET.Element) -> None:
    """Put <w> elements with @pos containing "RM" into a <note>."""
    parent_map = {c: p for p in root.iter() for c in p}
    for w in root.findall(".//tei:w", et_ns):
        if "RM" in w.get("pos", ""):
            parent = parent_map.get(w)
            if parent is not None and parent.tag != f"{ns['tei']}note":
                note = ET.Element(f"{ns['tei']}note", attrib={"type": "editorial"})
                parent.insert(list(parent).index(w), note)
                parent.remove(w)
                note.append(w)


def place_notes(root: ET.Element) -> None:
    """Place <note>'s to ignore tokens."""
    _normalize_div_type_notes(root)
    _note_redactional_comments(root)
    _put_last_enz_in_note(root)
    _move_xr_to_cit_in_note(root)
    _put_pos_999_in_note(root)
    _put_RM_in_note(root)
