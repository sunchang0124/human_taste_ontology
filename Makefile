ROBOT = java -jar bin/robot.jar
PREFIX = --prefix "HTO: http://purl.obolibrary.org/obo/HTO_"
TEMPLATES = $(wildcard src/templates/*.tsv)

.PHONY: all build reason report test clean imports interactions-doc verify-citations profiles

all: build

tmp:
	mkdir -p tmp

# Each template becomes a module, then everything merges.
tmp/%.owl: src/templates/%.tsv | tmp
	$(ROBOT) template --template $< $(PREFIX) --output $@

# The qualities module is the exception: its `SC HTO:0000061 some %` column
# references an object property declared in properties.tsv. Templated in
# isolation, ROBOT cannot know HTO:0000061 is an object property and emits a
# bare owl:DatatypeProperty declaration for it, which survives the merge and
# makes the released ontology OWL 2 DL invalid through punning. Passing the
# already-built properties module as --input gives ROBOT that context; it is
# used for typing only and none of its axioms are copied into the output. This
# explicit rule takes precedence over the pattern rule above.
tmp/qualities.owl: src/templates/qualities.tsv tmp/properties.owl | tmp
	$(ROBOT) template --input tmp/properties.owl --template $< $(PREFIX) --output $@

# profiles.tsv (I HTO:0000096 / I HTO:0000097, AT HTO:0000092) and
# interactions.tsv (I HTO:0000087 - I HTO:0000090) assert properties on named
# individuals, and both rules used to claim that templating them in isolation
# left ROBOT guessing at those properties' types, as it does for qualities.tsv.
# That was never true, and it was measured: for both templates the output is
# byte-identical with and without --input, because ROBOT types the property
# from the `I ` and `A ` column prefixes and needs no external declaration.
# The qualities.tsv rule above is the real case precisely because its
# `SC HTO:0000061 some %` column carries no such prefix: built without --input
# it emits HTO:0000061 and HTO:0000085 as owl:DatatypeProperty.
#
# The --input is kept on both rules as a guard against a future column that
# would need the typing, not because either template needs it today. A build
# comment asserting a mechanism that does not exist is the same failure class
# as a citation that does not support its claim, so this one says what is true.
tmp/profiles.owl: src/templates/profiles.tsv tmp/properties.owl | tmp
	$(ROBOT) template --input tmp/properties.owl --template $< $(PREFIX) --output $@

tmp/interactions.owl: src/templates/interactions.tsv tmp/properties.owl | tmp
	$(ROBOT) template --input tmp/properties.owl --template $< $(PREFIX) --output $@

MODULES = $(patsubst src/templates/%.tsv,tmp/%.owl,$(TEMPLATES))

build: $(MODULES) | tmp
	$(ROBOT) merge --input src/metadata.ttl \
	    $(foreach m,$(MODULES),--input $(m)) \
	    $(if $(wildcard src/imports/hto_imports.ttl),--input src/imports/hto_imports.ttl,) \
	  reason --reasoner ELK --equivalent-classes-allowed none \
	  annotate --ontology-iri "http://purl.obolibrary.org/obo/hto.owl" \
	           --version-iri "http://purl.obolibrary.org/obo/hto/$(shell date +%Y-%m-%d)/hto.owl" \
	  --output hto.owl
	$(ROBOT) convert --input hto.owl --format obo --output hto.obo
	$(ROBOT) convert --input hto.owl --format json --output hto.json

report: build
	$(ROBOT) report --input hto.owl --profile src/report_profile.txt --base-iri "http://purl.obolibrary.org/obo/HTO_" --output tmp/report.tsv --fail-on ERROR

validate: build
	python3 scripts/mappings2rdf.py
	python3 scripts/sheet2rdf.py data/raw/example_tasting.csv data/rdf/example.ttl --session example
	python3 scripts/published2rdf.py data/raw/published_tas2r38_prop.csv data/rdf/published.ttl
	python3 scripts/profile2rdf.py data/raw/example_profiles.csv data/rdf/profiles.ttl \
	    --tastants data/raw/example_food_tastants.csv \
	    --gap-report docs/needs-foodon.md
	python3 scripts/validate.py

test: report validate
	python3 -m pytest tests/ -q

clean:
	rm -rf tmp hto.owl hto.obo hto.json

interactions-doc:
	python3 scripts/interactions_md.py

verify-citations:
	python3 scripts/verify_citations.py

# Converts the *example* sheets only, and writes the committed gap report. To
# convert your own sheet, call the script directly with your own paths (see the
# README): --gap-report is passed explicitly here because docs/needs-foodon.md
# is a committed file rather than the script's default output location.
profiles:
	python3 scripts/profile2rdf.py data/raw/example_profiles.csv data/rdf/profiles.ttl \
	    --tastants data/raw/example_food_tastants.csv \
	    --gap-report docs/needs-foodon.md
