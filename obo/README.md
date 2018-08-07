This folder contains the context files for mapping DATS to the [OBO Foundry](http://www.obofoundry.org/) ontologies.

We have identified some entities and properties that are not available within the OBO ontologies, and this has been indicated as ```TODO``` on the mapping files, until those terms are added to the relevant ontologies.

The list of missing terms, which we will request to the relevant ontologies are:
- has_license (for dataset_distribution)
- conformsTo (for dataset_distribution)
- format (for dataset_distribution)
- creators (for dataset)
- in DATS.Dataset
```
 "distributions": {
      "@id": "obo:TODO -> distribution[missing term]",
      "type": "obo:TODO -> DataDownload[missing term]"
    },
   
```


Other issues:
- DATS.Dataset.acknowledges may have multiple types
```
"@type":["obo:OBI_0000245","obo:NCBITaxon_9606","obo:OBI_0001942","obo:OBI_0001636"]
```
but not all of them at the same time.
- DATS.Dataset.creators may have multiple values but not all of them at the same time, so we
cannot code

```
"creators":
    {
      "@id" : "obo:TODO",
      "@type":["obo:OBI_0000245","obo:NCBITaxon_9606"]
    }
```

- DATS.Dataset.producedBy multiple values
```
 "@type": ["OBI_0600013","OBI_0000066","OBI_0200000"]
```
 