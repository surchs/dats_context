# DATS JSON-LD context files

This repository contains [JSON-LD](http://json-ld.org/) context files for the DAta Tag Suite (DATS) model for describing datasets. These context files can be used in combination with the [DATS schemas](https://github.com/datatagsuite/schema). 

We provide context files that map the DATS elements to [schema.org](https://schema.org/). The schema.org context files are available [here](https://github.com/datatagsuite/context).

We also have context files mapping to the [OBO Foundry ontologies](https://github.com/biocaddie/WG3-MetadataSpecifications/tree/development/json-schemas/contexts/obofoundry). 

The context files can be accessed by persistent identifiers relying on the [w3id.org](http://w3id.org/) service. For example, the JSON-LD context file for the dataset object can be accessed through this URL: http://w3id.org/dats/context/sdo/dataset_sdo_context.jsonld

Consequently, if you want to use the context in a JSON file describing a dataset, you can include it as follows:
```
 {
   "@context", "http://w3id.org/dats/context/sdo/dataset_sdo_context.jsonld"
   ...
```
