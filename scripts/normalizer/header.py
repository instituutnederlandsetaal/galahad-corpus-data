"""Function for fixing issues in the `<teiHeader>`."""

import xml.etree.ElementTree as ET

from scripts.normalizer import et_ns, ns


def _move_source_desc(root: ET.Element) -> None:
    """
    Transform `<sourceDesc>`.

    transform <teiHeader> <sourceDesc> ... </sourceDesc> </teiHeader>
    to <teiHeader> <fileDesc> <sourceDesc> ... </sourceDesc> </fileDesc> </teiHeader>
    note that fileDesc may already be present, in which case we need to move sourceDesc into it
    and if there is already a sourceDesc in fileDesc, we delete it and prefer the one outside of fileDesc
    """
    header = root.find(".//tei:teiHeader", et_ns)
    if header is not None:
        source_desc = header.find("tei:sourceDesc", et_ns)
        if source_desc is not None:
            file_desc = header.find("tei:fileDesc", et_ns)
            if file_desc is None:
                file_desc = ET.Element(f"{ns['tei']}fileDesc")
                header.append(file_desc)
            orig_source_desc = file_desc.find("tei:sourceDesc", et_ns)
            if orig_source_desc is not None:
                file_desc.remove(orig_source_desc)
            # move sourceDesc into fileDesc
            header.remove(source_desc)
            file_desc.append(source_desc)


def _move_bron_to_source_desc(root: ET.Element) -> None:
    # move <bron> elements from <teiHeader> to <sourceDesc> renamed as <p>
    header = root.find(".//tei:teiHeader", et_ns)
    if header is not None:
        bron = header.find("tei:bron", et_ns)
        if bron is not None:
            file_desc = header.find("tei:fileDesc", et_ns)
            if file_desc is not None:
                source_desc = file_desc.find("tei:sourceDesc", et_ns)
                if source_desc is not None:
                    # create a <bibl> element and move the text of <bron> into it
                    bibl = ET.Element(f"{ns['tei']}bibl")
                    bibl.text = bron.text
                    source_desc.append(bibl)
                    # remove the original <bron> element
                    header.remove(bron)


def _remove_bron_not_found(root: ET.Element) -> None:
    """Remove `<bron_not_found>` elements in teiHeader."""
    header = root.find(".//tei:teiHeader", et_ns)
    if header is not None:
        for bron_not_found in header.findall("tei:bron_not_found", et_ns):
            header.remove(bron_not_found)


def _move_licence_to_p(root: ET.Element) -> None:
    # <publicationStmt> <availability> <licence> text </licence> </availability> </publicationStmt>
    # should be: <publicationStmt> <p> text </p> </publicationStmt>
    publication_stmt = root.find(".//tei:publicationStmt", et_ns)
    if publication_stmt is not None:
        availability = publication_stmt.find("tei:availability", et_ns)
        if availability is not None:
            # the usage of <availability> is only legal if a member of agency exists
            # these are: authority distributor publisher
            for agency_tag in ["authority", "distributor", "publisher"]:
                agency_elem = publication_stmt.find(f"tei:{agency_tag}", et_ns)
                if agency_elem is not None:
                    return

            licence = availability.find("tei:licence", et_ns)
            if licence is not None:
                # create a <p> element and move the text of <licence> into it
                p = ET.Element(f"{ns['tei']}p")
                p.text = licence.text
                publication_stmt.append(p)
                # remove the original <availability> element
                publication_stmt.remove(availability)

            # alternatively, <availability> contains some <p>'s
            # first check whether availability truly only contains <p>
            for child in availability:
                if child.tag != f"{ns['tei']}p":
                    return  # if not, do nothing

            # move these and then remove <availability)
            for child in availability:
                publication_stmt.append(child)
            publication_stmt.remove(availability)

            # and in this case, rename <idno> to <p> as well
            for idno in publication_stmt.findall("tei:idno", et_ns):
                idno.tag = f"{ns['tei']}p"


def _move_source_desc_p_to_bibl(root: ET.Element) -> None:
    # if <sourceDesc> contains at least one <listBibl>
    # rename all <p> to <bibl>
    source_desc = root.find(".//tei:sourceDesc", et_ns)
    if source_desc is not None and source_desc.find("tei:listBibl", et_ns) is not None:
        for p in source_desc.findall("tei:p", et_ns):
            p.tag = f"{ns['tei']}bibl"


def _move_bibl_scope_xref_attrs(root: ET.Element) -> None:
    # transform <biblScope> <xref to="..." from="..."/> </biblScope>
    # to <biblScope to="..." from="..." />
    for bibl_scope in root.findall(".//tei:biblScope", et_ns):
        xref = bibl_scope.find("tei:xref", et_ns)
        if xref is not None:
            for attr in ["to", "from"]:
                if attr in xref.attrib:
                    bibl_scope.set(attr, xref.get(attr))
            bibl_scope.remove(xref)


def _remove_couranten_source_desc_text(root: ET.Element) -> None:
    # sourceDesc may contain text directly, often a sibling of <interpGrp>
    # move this text into a <p> element (sibling of the <interpGrp>)
    source_desc = root.find(".//tei:sourceDesc", et_ns)
    if source_desc is not None:
        # get the tail of the interpGrp, which is the text after the last child element of sourceDesc
        list_bibl = source_desc.find("tei:listBibl", et_ns)
        if list_bibl is not None:
            text = list_bibl.tail
            if text:
                # remove the original text from sourceDesc
                list_bibl.tail = None


def _fixup_titles(root: ET.Element) -> None:
    # Some titles consist of just a number or whitespace\
    # in the former case, simply use the XML id (DBNL excerpts)
    # in the latter case (CLVN) lookup the title in the sourceDesc
    title = root.find(".//tei:title", et_ns)
    if title is not None:
        title_text = title.text.strip()
        xml_id = root.get(f"{ns['xml']}id", "")
        # If title is only digits or whitespace, use xml:id
        if title_text.isdigit():
            title.text = xml_id
        # If title is only whitespace, try to find a better title in sourceDesc
        elif not title_text:
            inl_metadata = root.find(".//tei:bibl[@type='textBron']", et_ns)
            title_interp_grp = inl_metadata.find(
                ".//tei:interpGrp[@type='title']",
                et_ns,
            )
            title_interp = title_interp_grp.find("./tei:interp", et_ns)
            title.text = title_interp.text


def _fixup_change_resp(root: ET.Element) -> None:
    # transform: <change> <respStmt> <name> ... </name> </respStmt> </change>
    # to: <change resp="..." />
    header = root.find(".//tei:teiHeader", et_ns)
    if header is not None:
        for change in header.findall(".//tei:change", et_ns):
            resp_stmt = change.find("tei:respStmt", et_ns)
            if resp_stmt is not None:
                name = resp_stmt.find("tei:name", et_ns)
                if name is not None and name.text:
                    change.set("resp", name.text)
                # remove the original respStmt
                change.remove(resp_stmt)

            # additionally, unwrap the text in <item>
            item = change.find("tei:item", et_ns)
            if item is not None and item.text:
                change.text = item.text
                change.remove(item)


def _fix_title_for_cit(root: ET.Element) -> None:
    """Give dictionary citations a title based on their lemma and sense-id."""
    cit = root.find(".//tei:cit", et_ns)
    if cit is None:
        return
    lemma = cit.get("lemma", "")
    sense_id = cit.get("sense-id", "")
    dictionary = "MNW" if sense_id.lower().startswith("mnw") else "WNT"
    title = f"{lemma} - {dictionary} ({sense_id})"

    header = root.find(".//tei:teiHeader", et_ns)
    if header is not None:
        file_desc = header.find("tei:fileDesc", et_ns)
        if file_desc is not None:
            title_stmt = file_desc.find("tei:titleStmt", et_ns)
            if title_stmt is not None:
                title_el = title_stmt.find("tei:title", et_ns)
                if title_el is not None:
                    # only change title if title is currently digit only
                    if title_el.text.isdigit():
                        title_el.text = title


def _put_agency_first(root: ET.Element) -> None:
    """If `<publicationStmt>` contains any `model.publicationStmtPart.agency`, make sure it is the first child element."""
    agency_tags = ["authority", "distributor", "publisher"]

    # first match will do
    pub_stmt = root.find(".//tei:publicationStmt", et_ns)
    if pub_stmt is not None:
        for tag in agency_tags:
            agency = pub_stmt.find(f"tei:{tag}", et_ns)
            if agency is not None:
                pub_stmt.remove(agency)
                pub_stmt.insert(0, agency)
                break


def _remove_date_from_pos_tagging_lancelot(root: ET.Element) -> None:
    """Remove `<date>` from <ab subtype="POS-tagging_lemmatisationProvenance2"> elements."""
    for ab in root.findall(
        './/tei:ab[@subtype="POS-tagging_lemmatisationProvenance2"]',
        et_ns,
    ):
        for date in ab.findall("tei:date", et_ns):
            ab.remove(date)


def _add_desc_to_non_text_interp(root: ET.Element) -> None:
    """Wrap all children of an `<interp>` in `<desc>` if the `<interp>` contains anything other than `<desc>` or plaintext."""
    for interp in root.findall(".//tei:interp", et_ns):
        child_tags: list[str] = [child.tag for child in interp]
        # skip if all children are <desc> or plaintext
        if len(child_tags) == 0 or all(tag == f"{ns['tei']}desc" for tag in child_tags):
            continue
        # wrap all children in <desc>, note any text
        desc = ET.Element(f"{ns['tei']}desc")
        desc.text = interp.text
        interp.text = None
        for child in list(interp):
            desc.append(child)
            interp.remove(child)
        interp.append(desc)


def _swap_x_for_ref(root: ET.Element) -> None:
    """Swap `<x @nr>` and `<XREF3 @ref>` elements for `<ref @n>` elements."""
    for x in root.findall(".//tei:x", et_ns):
        x.tag = f"{ns['tei']}ref"
        nr = x.get("nr")
        if nr is None:
            raise ValueError("<x> element missing 'nr' attribute")
        x.set("n", nr)
        del x.attrib["nr"]
    # same for <XREF3 @ref> elements
    for xref in root.findall(".//tei:XREF3", et_ns):
        xref.tag = f"{ns['tei']}ref"
        ref = xref.get("ref")
        if ref is None:
            raise ValueError("<XREF3> element missing 'ref' attribute")
        xref.set("n", ref)
        del xref.attrib["ref"]


def _remove_w_from_interp_grp(root: ET.Element) -> None:
    """Remove `<w>` elements from `<interpGrp>` elements."""
    # transform <interpGrp> <interp> <w> text </w> </interp> </interpGrp>
    # to <interpGrp> <interp>text</interp> </interpGrp>
    for interp_grp in root.findall(".//tei:interpGrp", et_ns):
        for interp in interp_grp.findall("tei:interp", et_ns):
            w = interp.find("tei:w", et_ns)
            if w is not None:
                text = "".join(w.itertext()).strip()
                interp.text = text
                interp.remove(w)


def normalize_tei_header(root: ET.Element) -> None:
    """Run all `<teiHeader>` fixes."""
    _move_source_desc(root)
    _move_bron_to_source_desc(root)
    _remove_bron_not_found(root)
    _move_licence_to_p(root)
    _move_source_desc_p_to_bibl(root)
    _move_bibl_scope_xref_attrs(root)
    _remove_couranten_source_desc_text(root)
    _remove_w_from_interp_grp(root)
    _add_desc_to_non_text_interp(root)
    _swap_x_for_ref(root)
    # important order:
    # will only fix title if it is currently digit only
    _fix_title_for_cit(root)
    # will add text to digit-only titles, so the former would no longer run
    _fixup_titles(root)
    _fixup_change_resp(root)
    _put_agency_first(root)
    _remove_date_from_pos_tagging_lancelot(root)
