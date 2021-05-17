import argparse
import json
import logging
import pathlib as pal
import urllib.error

import pandas as pd
import pandas.errors

CONTEXT_DIR = pal.Path("./dats_context/sdo")
SCHEMA_DIR = pal.Path("./schema")
REQUIRED_COLUMNS = ['schema', 'term', 'sdo_id', 'sdo_type']
SCHEMA_PROPS_URL = 'https://raw.githubusercontent.com/schemaorg/schemaorg/main/data/releases/12.0/schemaorg-all-http-properties.csv'
try:
    SDO_PROPERTIES = pd.read_csv(SCHEMA_PROPS_URL)
except urllib.error.HTTPError:
    # Resource unavailable or not internet access
    SDO_PROPERTIES = None

log = logging.getLogger()
log.addHandler(logging.StreamHandler())


def find_context_name(schema_name):
    return str(pal.Path(schema_name.replace('_schema', '_sdo_context')).with_suffix('.jsonld'))


def find_schema_name(context_name):
    return str(pal.Path(context_name.replace('_sdo_context', '_schema')).with_suffix('.json'))


def get_sdo_info(term):
    if 'sdo:' in term:
        term = term.strip('sdo:')
    if term in SDO_PROPERTIES.label.values:
        sdo_match = SDO_PROPERTIES.query('label==@term')
        sdo_description = sdo_match['comment'].values[0]
        sdo_domain = sdo_match['domainIncludes'].values[0]
        sdo_range = sdo_match['rangeIncludes'].values[0]
        return sdo_description, sdo_domain, sdo_range
    else:
        return None, None, None


def load_context(schema_dir, context_dir):
    schemas = {
        schema_f.name: json.load(open(schema_f))
        for schema_f in schema_dir.glob("*.json")
    }
    contexts = {
        context_f.name: json.load(open(context_f))
        for context_f in context_dir.glob("*.jsonld")
    }
    # Create a mapping of all terms defined in any context to any context they appear in
    context_keys = {}
    for context_name, context in contexts.items():
        for key in context['@context'].keys():
            if key not in context_keys.keys():
                context_keys[key] = []
            context_keys[key].append(context_name)

    return schemas, contexts, context_keys


def extract_mapping(mapping):
    if isinstance(mapping, dict):
        return mapping['@id'], mapping.get('@type')
    return mapping, None


def review_context(schemata, contexts, context_terms, with_missing=True, with_reusable=False, with_available=False):
    terms_list = []
    for schema_name, schema in schemata.items():
        context_name = find_context_name(schema_name)
        if context_name not in contexts:
            context = None
        else:
            context = contexts[context_name]

        for term in schema['properties'].keys():
            if '@' in term:
                continue
            description = schema['properties'][term].get('description')
            annotation = {'schema': schema_name,
                          'term': term,
                          'description': description,
                          'sdo_id': None,
                          'sdo_type': None
                          }
            if context is None or term not in context['@context']:
                # Is missing locally

                if term not in context_terms:
                    # Missing everywhere
                    annotation.update({'status': 'missing'})
                else:
                    # TODO: maybe ask user which match to use?
                    match = context_terms[term][0]
                    mapping = contexts[match]['@context'][term]
                    sdo_id, sdo_type = extract_mapping(mapping)
                    annotation.update({'status': 'reusable',
                                       'sdo_id': sdo_id,
                                       'sdo_type': sdo_type})
                    if with_reusable:
                        sdo_descr, sdo_domain, sdo_range = get_sdo_info(sdo_id)
                        annotation.update({'sdo_description': sdo_descr,
                                           'sdo_domain': sdo_domain,
                                           'sdo_range': sdo_range})
            else:
                sdo_id, sdo_type = extract_mapping(context['@context'][term])
                annotation.update({'status': 'available',
                                   'sdo_id': sdo_id,
                                   'sdo_type': sdo_type})
                if with_available:
                    sdo_descr, sdo_domain, sdo_range = get_sdo_info(sdo_id)
                    annotation.update({'sdo_description': sdo_descr,
                                       'sdo_domain': sdo_domain,
                                       'sdo_range': sdo_range})
            terms_list.append(annotation)
    # Filter everything we don't want
    annotation_table = pd.DataFrame(terms_list)
    log.info('Here is an overview of the status of terms in the context:\n', annotation_table.status.value_counts())
    status_list = [name for use, name in
                   zip([with_available, with_reusable, with_missing], ['available', 'reusable', 'missing']) if use]
    log.info(f'The output will include {",".join(status_list)} terms.')
    return annotation_table.query('status in @status_list')


def load_table(path):
    try:
        return pd.read_csv(path, sep=',')
    except pandas.errors.ParserError:
        # This might be tab separated, let's try that
        pass
    try:
        return pd.read_csv(path, sep='\t')
    except pandas.errors.ParserError as e:
        raise Exception(f'Could not load the table at {path.resolve()}. Make sure it is either comma or tab '
                        f'separated!') from e


def add_sdo_terms(table):
    terms = table['sdo_id']
    data = []
    for term in terms:
        if not isinstance(term, str):
            sdo_description = sdo_domain = sdo_range = None
        else:
            sdo_description, sdo_domain, sdo_range = get_sdo_info(term)
        data.append({'sdo_description': sdo_description,
                     'sdo_domain': sdo_domain,
                     'sdo_range': sdo_range})
    table.update(pd.DataFrame(data))
    return


def update_context(schemata, contexts, annotations, clobber=False):
    '''
    Read a mapping and create a new or updated context with these mappings
    either overwrite old stuff or not

    :return:
    '''
    updated_contexts = {}
    for schema_name, schema in schemata.items():
        context_name = find_context_name(schema_name)
        if context_name not in contexts:
            context = {'@context': {'sdo': 'https://schema.org/'}}
        else:
            context = contexts[context_name]

        for term in schema['properties'].keys():
            if '@' in term:
                continue
            # Find any annotations for this term and schema
            annotation_match = annotations.query('schema == @schema_name and term == @term and not sdo_id.isnull()',
                                                 engine='python')
            if not annotation_match.empty:
                sdo_id = annotation_match.get('sdo_id').values[0]
                sdo_type = annotation_match.get('sdo_type').values[0]
                # If sdo_type is not annotated, it'll be NaN or empty string
                if not sdo_type or not isinstance(sdo_type, str):
                    mapping = sdo_id
                else:
                    mapping = {'@id': sdo_id, '@type': sdo_type}
                if term in context['@context'].keys() and not mapping == context['@context'].get(term) and not clobber:
                    # Will ignore this term even though it is annotated
                    log.warning(f'{schema_name}:{term} has new {mapping = } but will be ignored because it '
                                f'already exists and {clobber = }. Old mapping is {context["@context"].get(term)}')
                    continue

                context['@context'][term] = mapping
        updated_contexts[str(context_name)] = context
    return updated_contexts


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='''
            This tool can do three things:
            - mode:"review": Take the existing context (by default expected in ./context) and write it to a table for review
            - mode:"add_sdo": Take a review table that was manually annotated and add the description, domain, and range of the annotated schema.org properties
            - mode:"update": Take a review table and use the included annotations to create an extended context, overwriting the old or creating a new folder
        '''
    )
    parser.add_argument('mode', choices=['review', 'add_sdo', 'update'], help='chose the mode', type=str)
    parser.add_argument('out', type=pal.Path, help="Where to put the output (default = in the same folder).")
    parser.add_argument('-a', '--annotation', help='specify the path to the annotation table you want to use'
                                                   'to augment the context', type=pal.Path)
    parser.add_argument('-s',
                        '--schema_dir',
                        type=pal.Path,
                        help='''The path to the DATS schema''', default=SCHEMA_DIR
                        )
    parser.add_argument('-c', '--context_dir', type=pal.Path, help='''The path to the DATS schema.org context''',
                        default=CONTEXT_DIR)

    parser.add_argument('-wa', '--with_available', action='store_true', help='include available terms')
    parser.add_argument('-wm', '--with_missing', action='store_true', help='include missing terms')
    parser.add_argument('-wr', '--with_reusable', action='store_true', help='include reusable terms')
    args = parser.parse_args()

    if args.mode == 'review':
        # Write a table with the current context
        # May include missing, available, and reusable terms
        schemas, contexts, context_keys = load_context(args.schema_dir, args.context_dir)
        review_table = review_context(schemata=schemas, contexts=contexts, context_terms=context_keys,
                                      with_missing=args.with_missing,
                                      with_reusable=args.with_reusable,
                                      with_available=args.with_available)
        review_table.to_csv(args.out, index=False)
    elif args.mode == 'add_sdo':
        if SDO_PROPERTIES is None:
            raise Exception(f'Could not load the SDO property dictionary from {SCHEMA_PROPS_URL}, check your network '
                            f'access')
        table = load_table(args.input)
        if not set(REQUIRED_COLUMNS).issubset(table.columns):
            raise Exception(f'Please make sure the annotation has the following column headers: {REQUIRED_COLUMNS}')
        add_sdo_terms(table)
        table.to_csv(args.out, index=False)
    elif args.mode == 'update':
        schemas, contexts, context_keys = load_context(args.schema_dir, args.context_dir)
        annotations = load_table(args.annotation)
        if not set(REQUIRED_COLUMNS).issubset(annotations.columns):
            raise Exception(f'Please make sure the annotation has the following column headers: {REQUIRED_COLUMNS}')
        updated_contexts = update_context(schemata=schemas, contexts=contexts, annotations=annotations)
        if not args.out.is_dir():
            log.info(f'Creating new output directory: {args.out.resolve()}')
            args.out.mkdir()
        # Write the updated contexts to disk
        log.info(f'Writing new context files to {args.out.resolve()}')
        for context_name, context in updated_contexts.items():
            json.dump(context, open(args.out / context_name, 'w'), indent=2)
