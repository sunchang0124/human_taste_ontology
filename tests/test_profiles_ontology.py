"""The taste-profile layer's ontology terms: properties, vocabularies, interactions."""
import pathlib
import rdflib
from rdflib.namespace import OWL, RDF, RDFS

ROOT = pathlib.Path(__file__).resolve().parent.parent
HTO = "http://purl.obolibrary.org/obo/HTO_"


def graph():
    g = rdflib.Graph()
    g.parse(ROOT / "hto.owl", format="xml")
    return g


def term(local):
    return rdflib.URIRef(HTO + local)


def curie_iri(curie):
    """Resolve any OBO-style CURIE (HTO:, CHEBI:, ...) to its full IRI. Both
    prefixes used here share the http://purl.obolibrary.org/obo/PREFIX_LOCAL
    pattern, so one resolver covers both."""
    prefix, local = curie.split(":", 1)
    return rdflib.URIRef(f"http://purl.obolibrary.org/obo/{prefix}_{local}")


# (label, owl_type, domain CURIE or None, range CURIE or None). Domain/range
# taken verbatim from Task 1 brief Step 4's table, including the deliberately
# empty cells (HTO:0000080/0000086 domains; HTO:0000092/0000095 domain+range).
NEW_PROPERTIES = {
    "0000080": ("has profile entry", OWL.ObjectProperty, None, "HTO:0000400"),
    "0000081": ("entry quality", OWL.ObjectProperty, "HTO:0000400", "HTO:0000100"),
    "0000082": ("entry level", OWL.ObjectProperty, "HTO:0000400", "HTO:0000200"),
    "0000083": ("entry phase", OWL.ObjectProperty, "HTO:0000400", "HTO:0000210"),
    "0000084": ("holds for group", OWL.ObjectProperty, "HTO:0000400", "HTO:0000220"),
    "0000085": ("elicited by tastant", OWL.ObjectProperty, "HTO:0000100", "CHEBI:24431"),
    "0000086": ("contains tastant", OWL.ObjectProperty, None, "CHEBI:24431"),
    "0000087": ("interaction agent", OWL.ObjectProperty, "HTO:0000410", "HTO:0000100"),
    "0000088": ("interaction target", OWL.ObjectProperty, "HTO:0000410", "HTO:0000100"),
    "0000089": ("interaction effect", OWL.ObjectProperty, "HTO:0000410", "HTO:0000230"),
    "0000090": ("demonstrated with", OWL.ObjectProperty, "HTO:0000410", "CHEBI:24431"),
    "0000091": ("explained by interaction", OWL.ObjectProperty, "HTO:0000400", "HTO:0000410"),
    "0000092": ("level rank", OWL.AnnotationProperty, None, None),
    # NOTE: ROBOT's template keyword for a data property is `owl:DataProperty`
    # (see properties.tsv's TYPE column); OWL serialises it as
    # `owl:DatatypeProperty`, which is what rdflib reads back here. Writing
    # `owl:DatatypeProperty` in the template itself is a different, silent
    # bug: ROBOT does not recognise it as a keyword and instead CURIE-resolves
    # it, declaring the subject a named individual of it - illegal
    # property/individual punning that also drops the term from hto.obo.
    "0000093": ("source statement", OWL.DatatypeProperty, "HTO:0000400", None),
    "0000094": ("has evidence type", OWL.ObjectProperty, "HTO:0000400", "HTO:0000240"),
    "0000095": ("interaction condition", OWL.AnnotationProperty, None, None),
    "0000096": ("group defined by status", OWL.ObjectProperty, "HTO:0000223", "HTO:0000011"),
    "0000097": ("group defined by diplotype", OWL.ObjectProperty, "HTO:0000222", "HTO:0000015"),
}


def test_every_new_property_is_declared_with_the_right_type_and_label():
    g = graph()
    for local, (label, owl_type, _domain, _range) in NEW_PROPERTIES.items():
        subject = term(local)
        assert (subject, RDF.type, owl_type) in g, f"{local} {label}: wrong or missing type"
        assert (subject, RDFS.label, rdflib.Literal(label)) in g, f"{local}: label mismatch"


def test_every_new_property_has_the_expected_domain_and_range():
    """A property whose keyword ROBOT does not recognise silently loses its
    domain/range (see HTO:0000093's history) rather than failing the build,
    so type-checking alone is not enough."""
    g = graph()
    for local, (label, _owl_type, domain, range_) in NEW_PROPERTIES.items():
        subject = term(local)
        domains = set(g.objects(subject, RDFS.domain))
        ranges = set(g.objects(subject, RDFS.range))
        expected_domains = {curie_iri(domain)} if domain else set()
        expected_ranges = {curie_iri(range_)} if range_ else set()
        assert domains == expected_domains, (
            f"{local} {label}: domain {sorted(domains)}, expected {sorted(expected_domains)}"
        )
        assert ranges == expected_ranges, (
            f"{local} {label}: range {sorted(ranges)}, expected {sorted(expected_ranges)}"
        )


def test_every_new_property_carries_exactly_its_intended_type():
    """Scoped to the 18 new properties only: the HTO:0000015 / HTO:0000012-14
    class/individual punning sanctioned by ruling R3 is a different,
    deliberate case and must not be flagged here."""
    g = graph()
    for local, (label, owl_type, _domain, _range) in NEW_PROPERTIES.items():
        types = set(g.objects(term(local), RDF.type))
        assert types == {owl_type}, f"{local} {label}: types {sorted(types)}, expected only {owl_type}"


def test_every_new_property_carries_a_definition():
    """missing_definition is an ERROR in src/report_profile.txt, so a property
    without IAO:0000115 fails the build, not just this test."""
    g = graph()
    definition = rdflib.URIRef("http://purl.obolibrary.org/obo/IAO_0000115")
    for local in NEW_PROPERTIES:
        assert (term(local), definition, None) in g, f"{local} has no definition"


def test_chemical_entity_is_imported():
    g = graph()
    assert (rdflib.URIRef("http://purl.obolibrary.org/obo/CHEBI_24431"), RDFS.label, None) in g


VOCABULARY = {
    "0000200": ["0000201", "0000202", "0000203", "0000204", "0000205"],
    "0000210": ["0000211", "0000212", "0000213", "0000214"],
    "0000230": ["0000231", "0000232"],
    "0000240": ["0000241", "0000242", "0000243", "0000244"],
}
RANKS = {"0000201": 0, "0000202": 1, "0000203": 2, "0000204": 3, "0000205": 4}


def test_slot_vocabularies_contain_exactly_the_enumerated_members():
    """Closed lists. A member appearing that the converter does not know about
    would be accepted by the ontology and rejected by the sheet, silently."""
    g = graph()
    for parent, members in VOCABULARY.items():
        found = {str(s).replace(HTO, "") for s in g.subjects(RDF.type, term(parent))}
        assert found == set(members), f"{parent}: expected {members}, found {sorted(found)}"


def test_intensity_levels_are_ranked_zero_to_four():
    g = graph()
    rank = term("0000092")
    for local, expected in RANKS.items():
        values = [int(o) for o in g.objects(term(local), rank)]
        assert values == [expected], f"{local}: rank {values}, expected [{expected}]"


def test_taster_groups_point_back_at_the_v1_core():
    """A group is not a new parallel vocabulary: genotype groups name an
    HTO:0000015 diplotype, phenotype groups name an HTO:0000011 taster status."""
    g = graph()
    by_diplotype, by_status = term("0000097"), term("0000096")
    assert (term("0000224"), by_diplotype, None) in g
    assert (term("0000226"), by_diplotype, None) in g
    assert (term("0000227"), by_status, term("0000012")) in g
    assert (term("0000229"), by_status, term("0000014")) in g


def test_the_two_reified_classes_exist():
    g = graph()
    for local in ("0000400", "0000410"):
        assert (term(local), RDF.type, OWL.Class) in g


ELICITATION = {
    "0000111": "CHEBI_17992",  # sweetness      <- sucrose
    "0000112": "CHEBI_30769",  # sourness       <- citric acid
    "0000113": "CHEBI_26710",  # saltiness      <- sodium chloride
    "0000115": "CHEBI_16015",  # umami          <- L-glutamic acid
    "0000131": "CHEBI_8502",   # thiourea bitterness  <- PROP
    "0000132": "CHEBI_16226",  # limonoid bitterness  <- limonin
    "0000133": "CHEBI_28819",  # flavanone bitterness <- naringin
    "0000134": "CHEBI_27732",  # alkaloid bitterness  <- caffeine
}


def test_qualities_are_linked_to_the_tastants_that_elicit_them():
    """Each link is an existential restriction, not an annotation: cq13 walks it
    to find foods containing a tastant whose quality nobody has annotated."""
    g = graph()
    elicited_by = term("0000085")
    for quality, chebi in ELICITATION.items():
        found = False
        for restriction in g.objects(term(quality), RDFS.subClassOf):
            if (restriction, OWL.onProperty, elicited_by) in g and (
                restriction,
                OWL.someValuesFrom,
                rdflib.URIRef("http://purl.obolibrary.org/obo/" + chebi),
            ) in g:
                found = True
        assert found, f"HTO:{quality} is not linked to {chebi}"


def test_the_two_precoordinated_temporal_terms_name_their_preferred_form():
    g = graph()
    for local in ("0000153", "0000154"):
        comments = " ".join(str(c) for c in g.objects(term(local), RDFS.comment))
        assert "finish" in comments.lower(), f"HTO:{local} does not name the preferred form"
