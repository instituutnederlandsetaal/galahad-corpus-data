"""Functions for fixing various xml attributes."""

import re
import xml.etree.ElementTree as ET

from scripts.normalizer import et_ns, ns


def _normalize_root_xml_id(root: ET.Element) -> None:
    """
    Give the root a valid @xml:id (may not start with a number).

    Raises:
        ValueError: Could not find any suitable value for @xml:id.
    """
    # Check for an xml:id on the root
    if f"{ns['xml']}id" not in root.attrib:
        # try to find it in text/@xml:id
        text_elem = root.find(".//tei:text[@xml:id]", et_ns)
        xmlid = (
            text_elem.get("{" + ns["xml"] + "}id") if text_elem is not None else None
        )
        if xmlid is None:
            # use <idno type="pid">UUID</idno> if present
            idno_elem = root.find(".//tei:idno[@type='pid']", et_ns)
            xmlid = idno_elem.text if idno_elem is not None else None
            if xmlid is None:
                # use <interpGrp type="pid"><interp>UUID</interp></interpGrp>
                interp = root.find(".//tei:interpGrp[@type='pid']/tei:interp", et_ns)
                xmlid = interp.text if interp is not None else None
                # might be in interp/@value
                if xmlid is None and interp is not None:
                    xmlid = interp.get("value")

                if xmlid is None:
                    # use cit/@xml:id if present
                    cit_elem = root.find(".//tei:cit", et_ns)
                    xmlid = (
                        cit_elem.get(f"{ns['xml']}id") if cit_elem is not None else None
                    )
                    if xmlid is not None:
                        xmlid = f"pid_{xmlid}"

        if xmlid is None:
            raise ValueError("Could not find any suitable value for @xml:id.")
        # set it
        root.set(f"{ns['xml']}id", xmlid)

    # now, retrieve the xml id once more, either just added or already present
    xmlid = root.get(f"{ns['xml']}id")
    # if xml id matches UUID regex or start with a number
    if re.match(
        r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
        xmlid,
    ):
        xmlid = f"pid_{xmlid}"
        # readd
        root.set(f"{ns['xml']}id", xmlid)


def _remove_illegal_attributes(root: ET.Element) -> None:
    """Remove various illegal attributes grouped by tag."""
    illegal_attrs = {
        (".//tei:w", ".//tei:pc"): [
            "lexicon",
            "corresp",
            "changed",
            "gloss",
            "misAlignment",
            "feest",
            "lemmaRef",
            "time",
            "valid",
            "originalContent",
            "ctag",
            "mform",
            "org",
        ],
        (".//tei:teiHeader",): ["type"],
        (".//tei:xr",): ["extent"],
        (".//tei:s",): ["fixed"],
    }

    for tag_list, attrs in illegal_attrs.items():
        nodes = []
        for tag in tag_list:
            nodes.extend(root.findall(tag, et_ns))
        for node in nodes:
            for attr in attrs:
                if attr in node.attrib:
                    del node.attrib[attr]


def _rename_old_pos_to_type(root: ET.Element) -> None:
    """Rename @old_pos to @type on `<w>` and `<pc>` elements."""
    for el in root.findall(".//tei:w", et_ns) + root.findall(".//tei:pc", et_ns):
        if "old_pos" in el.attrib:
            el.set("type", el.get("old_pos"))
            del el.attrib["old_pos"]


def _remove_empty_type_in_w_and_pc(root: ET.Element) -> None:
    """Remove @type if empty in `<w>` and `<pc>` elements."""
    for el in root.findall(".//tei:w", et_ns) + root.findall(".//tei:pc", et_ns):
        if el.get("type") is not None and not el.get("type"):
            del el.attrib["type"]


def _move_list_bibl_id_to_xml_id(root: ET.Element) -> None:
    """If `<listBibl>` has an @id, turn it into an @xml:id."""
    for list_bibl in root.findall(".//tei:listBibl", et_ns):
        if "id" in list_bibl.attrib:
            list_bibl.set(f"{ns['xml']}id", list_bibl.get("id"))
            del list_bibl.attrib["id"]


def _move_fs_xml_id_to_n(root: ET.Element) -> None:
    """If `<fs>` has an @xml:id, move it to @n."""
    for fs in root.findall(".//tei:fs", et_ns):
        if f"{ns['xml']}id" in fs.attrib:
            fs.set("n", fs.get(f"{ns['xml']}id"))
            del fs.attrib[f"{ns['xml']}id"]


def _fixup_w_xml_id(root: ET.Element) -> None:
    """Prefix @xml:id with 'w' if it starts with a number on `<w>` and `<pc>` elements."""
    for w in root.findall(".//tei:w", et_ns) + root.findall(".//tei:pc", et_ns):
        xml_id = w.get(f"{ns['xml']}id")
        if xml_id is not None and re.match(r"^[0-9]", xml_id):
            w.set(f"{ns['xml']}id", f"w{xml_id}")


def _move_interp_value_to_text(root: ET.Element) -> None:
    """If `<interp>` has a @value, move it to the text content of the element."""
    for interp in root.findall(".//tei:interp", et_ns):
        if "value" in interp.attrib:
            interp.text = interp.get("value")
            del interp.attrib["value"]


def _move_text_in_pb_to_n(root: ET.Element) -> None:
    """Move `<pb>` text `</pb>` to `<pb n="text"/>`."""
    for pb in root.findall(".//tei:pb", et_ns):
        if pb.text:
            pb.set("n", pb.text)
            pb.text = None


def _remove_slash_apostrophe_in_lemma(root: ET.Element) -> None:
    """Remove \' in the @lemma attribute of `<w>` elements."""
    for w in root.findall(".//tei:w", et_ns):
        lemma = w.get("lemma")
        if lemma:
            w.set("lemma", lemma.replace("\\'", "'"))


def normalize_attributes(root: ET.Element) -> None:
    """Run all attribute normalization functions."""
    _normalize_root_xml_id(root)
    _remove_illegal_attributes(root)
    _rename_old_pos_to_type(root)
    _remove_empty_type_in_w_and_pc(root)
    _move_list_bibl_id_to_xml_id(root)
    _move_fs_xml_id_to_n(root)
    _fixup_w_xml_id(root)
    _move_interp_value_to_text(root)
    _move_text_in_pb_to_n(root)
    _remove_slash_apostrophe_in_lemma(root)
