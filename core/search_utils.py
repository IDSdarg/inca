'''
This file provides basic search functionality for the INCA database.
'''
from core.database import client as _client
from core.database import scroll_query as _scroll_query
from core.database import elastic_index as _elastic_index
from core.database import DATABASE_AVAILABLE as _DATABASE_AVAILABLE
import logging as _logging
from core.basic_utils import dotkeys as _dotkeys
import _datetime as _datetime

_logger = _logging.getLogger(__name__)

def list_doctypes():
    if not _DATABASE_AVAILABLE:
        _logger.warning("Could not list documents: No database instance available")
        return []
    existing_doctypes = [key for key in _client.indices.get_mapping(_elastic_index).get(_elastic_index,{}).get('mappings',{}).keys() if
                         key != '_default_' and key != 'core.document']
    overview = {doctype:_client.search(index=_elastic_index,doc_type=doctype).get('hits',{}).get('total',"NA") for
                                                                                        doctype in existing_doctypes}
    return overview

def doctype_generator(doctype):
    _logger.warning("Filter has been replaced by query, still need to test whether edge cases might be unintentionally returned")
    query = {'query':{'match':{'_type':doctype}}}
    for num, doc in enumerate(_scroll_query(query)):
        if not _DATABASE_AVAILABLE:
            _logger.warning("Could not get documents: No database instance available")
            break
        _logger.info("returning {num}".format(**locals()))
        yield doc

def doctype_first(doctype, num=1, by_field="META.ADDED"):
    '''Returns the first document of a given doctype

    Input
    ---
    doctype: string
        The document type you whish to retrieved
    num: int
        The number of documents to retrieve
    by_field: string
        The _datetime field by which to determine the
        first document
    '''
    if not _DATABASE_AVAILABLE:
        _logger.warning("Could not get first document: No database instance available")
        return []
    docs = _client.search(index=_elastic_index,
                  body={
                      "sort": [
                          {by_field : {"order":"asc"}}
                          ],
                      "size":num,
                      "query":
                      {"match":
                       {"doctype":
                        doctype
                       }
                      }}).get('hits',{}).get('hits',[""])
    return docs

def doctype_last(doctype,num=1, by_field="META.ADDED"):
    '''Returns the last document of a given doctype

    Input
    ---
    doctype: string
        The document type you whish to retrieved
    num: int
        The number of documents to retrieve
    by_field: string
        The _datetime field by which to determine the
        last document
    '''
    if not _DATABASE_AVAILABLE:
        _logger.warning("Could not get last documents: No database instance available")
        return []
    docs = _client.search(index=_elastic_index,
                  body={
                      "sort": [
                          { by_field : {"order":"desc"}}
                          ],
                      "size":num,
                      "query":
                      {"match":
                       {"doctype":
                        doctype
                       }
                      }}).get('hits',{}).get('hits',[""])
    return docs

def doctype_examples(doctype, field=None, seed=42, num=10):
    if not _DATABASE_AVAILABLE:
        _logger.warning("Could not get example documents: No database instance available")
        return []
    docs = _client.search(index=_elastic_index, body={
        'size':num,
        "query": {
            "function_score": {
                "query": {

                        "match": {
                            "_type": doctype
                            }

                    },
                "functions": [
                    {
                        "random_score": {
                            "seed": seed
                            }
                        }
                    ]
                }}
    })
    if not field:
        return docs['hits']['hits']
    elif type(field)==str:
        return [_dotkeys(doc,field) for doc in docs['hits']['hits']]
    else:
        return [{fi:_dotkeys(doc,fi) for fi in field} for doc in docs['hits']['hits']]

def doctype_fields(doctype):
    '''
    returns a summary of fields for documents of `doctype`:
    field : type - count (coverage)

    note:
        As elasticsearch does not natively support an 'all fields' query,
        this function runs a 1000 document sample and takes the union of
        found keys as a proxy of fields shared by all documents.
    '''
    if not _DATABASE_AVAILABLE:
        _logger.warning("Could not get document information: No database instance available")
        return []
    from collections import Counter
    key_count = Counter()
    doc_num   = _client.search(index=_elastic_index, body={'query':{'match':{'doctype':doctype}}})['hits']['total']
    mappings = _client.indices.get_mapping(_elastic_index).get(_elastic_index,{}).get('mappings',{}).get(doctype,{}).get('properties',{})
    coverage = {key:_client.search(_elastic_index,body={'query': {'bool':{'filter':[{'exists':{'field':key}},{'term':{'doctype':doctype}}]}}}).get('hits',{}).get('total',0) for key in mappings.keys() if key!="META"}
    summary = {k:{'coverage':coverage.get(k,'unknown')/float(doc_num),'type':mappings[k].get('type','unknown')} for
               k in mappings.keys() if k!="META"}
    return summary

def missing_field(doctype=None, field='_source', stats_only=True):
    if not _DATABASE_AVAILABLE:
        _logger.warning("Could not get documents missing a field: No database instance available")
        return []
    query = {'filter':{'missing':{'field':field}}}
    if not doctype:
        result = _client.search(_elastic_index, body=query)
    else:
        result = _client.search(_elastic_index, doctype, body=query)
    if not stats_only:
        return result['hits']['hits']
    else:
        total = doctype and _client.search(_elastic_index, doctype)['hits']['total'] or _client.search(_elastic_index)['hits']['total']
        stats = {
            'doctype' : doctype and doctype or '*',
            'field' : field,
            'missing': result['hits']['total'],
            'total'  : total,
            'percentage_missing' : ((result['hits']['total'])/(total*1.))*100
        }

        return stats
def doctype_inspect(doctype):
    '''Show some information about documents of a specified type

    Parameters
    ----------
    doctype : string
        string specifying the doctype to examine (see list_doctypes for available documents)

    Returns
    -------
    dictionary
        summary of documents of the specified type:
            total collected : integer
                the amount of documents of this type (approximation)
            first_collected : _datetime
                the minimal 'META.ADDED' field of these documents, which
                specifies the oldest documents
            last_collected : _datetime
                the maximum 'META.ADDED' field of these documents which
                specifies when the last document of this type was collected
            keys : dictionary
                <keyname> : dictionary
                    coverage : float
                        the proportion of documents that have this key
                    type     : string
                        the elasticsearch index type of this field

    '''

    firstdocs = doctype_first(doctype, by_field="META.ADDED")
    lastdocs  = doctype_last(doctype, by_field="META.ADDED")

    summary = dict(
        total_collected = _client.search(index=_elastic_index, doc_type=doctype)['hits']['total'],
        first_collected = firstdocs and firstdocs[0].get('_source',{}).get('META',{}).get("ADDED",None) or None,
        last_collected = lastdocs and lastdocs[0].get('_source',{}).get('META',{}).get("ADDED",None),
        keys=doctype_fields(doctype)
    )


    return summary
