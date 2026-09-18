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


NEW_PROPERTIES = {
    "0000080": ("has profile entry", OWL.ObjectProperty),
    "0000081": ("entry quality", OWL.ObjectProperty),
    "0000082": ("entry level", OWL.ObjectProperty),
    "0000083": ("entry phase", OWL.ObjectProperty),
    "0000084": ("holds for group", OWL.ObjectProperty),
    "0000085": ("elicited by tastant", OWL.ObjectProperty),
    "0000086": ("contains tastant", OWL.ObjectProperty),
    "0000087": ("interaction agent", OWL.ObjectProperty),
    "0000088": ("interaction target", OWL.ObjectProperty),
    "0000089": ("interaction effect", OWL.ObjectProperty),
    "0000090": ("demonstrated with", OWL.ObjectProperty),
    "0000091": ("explained by interaction", OWL.ObjectProperty),
    "0000092": ("level rank", OWL.AnnotationProperty),
    "0000093": ("source statement", OWL.DatatypeProperty),
    "0000094": ("has evidence type", OWL.ObjectProperty),
    "0000095": ("interaction condition", OWL.AnnotationProperty),
    "0000096": ("group defined by status", OWL.ObjectProperty),
    "0000097": ("group defined by diplotype", OWL.ObjectProperty),
}


def test_every_new_property_is_declared_with_the_right_type_and_label():
    g = graph()
    for local, (label, owl_type) in NEW_PROPERTIES.items():
        subject = term(local)
        assert (subject, RDF.type, owl_type) in g, f"{local} {label}: wrong or missing type"
        assert (subject, RDFS.label, rdflib.Literal(label)) in g, f"{local}: label mismatch"


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
