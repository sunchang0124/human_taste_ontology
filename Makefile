ROBOT = java -jar bin/robot.jar
PREFIX = --prefix "HTO: http://purl.obolibrary.org/obo/HTO_"
TEMPLATES = $(wildcard src/templates/*.tsv)

.PHONY: all build reason report test clean imports

all: build

tmp:
	mkdir -p tmp

# Each template becomes a module, then everything merges.
tmp/%.owl: src/templates/%.tsv | tmp
	$(ROBOT) template --template $< $(PREFIX) --output $@

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
	python3 scripts/validate.py

test: report validate
	python3 -m pytest tests/ -q

clean:
	rm -rf tmp hto.owl hto.obo hto.json
