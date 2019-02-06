from __future__ import print_function, absolute_import, unicode_literals, division


import yaml
from yaml import MarkedYAMLError
import glob
import os
import logging
import six
import collections

class NoDefault(object):
    def __str__(self):
        return "No default data"


NO_DEFAULT = NoDefault()

def read_version_from_json_file():
    try:
        with open(os.path.join(os.path.dirname(__file__), "version.json")) as f:
            return yaml.safe_load(f)['__version__']
    except ValueError:
        print("Json File Not Valid: setting version to 0.0.0")
        return "0.0.0"

__version__ = read_version_from_json_file()


class YamlMergeError(Exception):
    pass


def data_merge(a, b, unique_list=False, key_on='name'):
    """merges b into a and return merged result
    based on http://stackoverflow.com/questions/7204805/python-dictionaries-of-dictionaries-merge
    and extended to also merge arrays and to replace the content of keys with the same name

    NOTE: tuples and arbitrary objects are not handled as it is totally ambiguous what should happen"""
    key = None
    # ## debug output
    # sys.stderr.write("DEBUG: %s to %s\n" %(b,a))
    try:
        if a is None or isinstance(a, (six.string_types, float, six.integer_types)):
            # border case for first run or if a is a primitive
            a = b
        elif isinstance(a, list):
            # lists can be only appended
            if isinstance(b, list):
                # merge lists
                a.extend(b)
            else:
                # append to list
                a.append(b)
            if unique_list:
                if len(a) > 0 and isinstance(a[0], dict):
                    a = {v[key_on]:v for v in a}.values()
                else:
                    a = list(set(a))
        elif isinstance(a, dict):
            # dicts must be merged
            if isinstance(b, dict):
                for key in b:
                    if key in a:
                        a[key] = data_merge(a[key], b[key], unique_list=unique_list, key_on=key_on)
                    else:
                        a[key] = b[key]
            else:
                raise YamlMergeError('Cannot merge non-dict "%s" into dict "%s"' % (b, a))
        else:
            raise YamlMergeError('NOT IMPLEMENTED "%s" into "%s"' % (b, a))
    except TypeError as e:
        raise YamlMergeError('TypeError "%s" in key "%s" when merging "%s" into "%s"' % (e, key, b, a))
    return a


def yaml_load(source, defaultdata=NO_DEFAULT, unique_list=False, key_on='name'):
    """merge YAML data from files found in source

    Always returns a dict. The YAML files are expected to contain some kind of
    key:value structures, possibly deeply nested. When merging, lists are
    appended and dict keys are replaced. The YAML files are read with the
    yaml.safe_load function.

    source can be a file, a dir, a list/tuple of files or a string containing
    a glob expression (with ?*[]).

    For a directory, all *.yaml files will be read in alphabetical order.

    defaultdata can be used to initialize the data.
    """
    logger = logging.getLogger(__name__)
    logger.debug("initialized with source=%s, defaultdata=%s", source, defaultdata)
    if defaultdata is NO_DEFAULT:
        data = None
    else:
        data = defaultdata
    files = []
    if type(source) is not str and len(source) == 1:
        # when called from __main source is always a list, even if it contains only one item.
        # turn into a string if it contains only one item to support our different call modes
        source = source[0]
    if type(source) is list or type(source) is tuple:
        # got a list, assume to be files
        files = source
    elif os.path.isdir(source):
        # got a dir, read all *.yaml files
        files = sorted(glob.glob(os.path.join(source, "*.yaml")))
    elif os.path.isfile(source):
        # got a single file, turn it into list to use the same code
        files = [source]
    else:
        # try to use the source as a glob
        files = sorted(glob.glob(source))
    if files:
        logger.debug("Reading %s\n", ", ".join(files))
        for yaml_file in files:
            try:
                with open(yaml_file) as f:
                    new_data = yaml.safe_load(f)
                logger.debug("YAML LOAD: %s", new_data)
            except MarkedYAMLError as e:
                logger.error("YAML Error: %s", e)
                raise YamlMergeError("YAML Error: %s" % str(e))
            if new_data is not None:
                data = data_merge(data, new_data, unique_list=unique_list, key_on=key_on)
    else:
        if defaultdata is NO_DEFAULT:
            logger.error("No YAML data found in %s and no default data given", source)
            raise YamlMergeError("No YAML data found in %s" % source)

    return data

def construct_ordereddict(loader, node):
    try:
        omap = loader.construct_yaml_omap(node)
        return collections.OrderedDict(*omap)
    except yaml.constructor.ConstructorError:
        return loader.construct_yaml_seq(node)


def represent_ordereddict(dumper, data):
    # NOTE: For block style this uses the compact omap notation, but for flow style
    # it does not.
    values = []
    node = yaml.SequenceNode(u'tag:yaml.org,2002:omap', values, flow_style=False)
    if dumper.alias_key is not None:
        dumper.represented_objects[dumper.alias_key] = node
    for key, value in data.items():
        key_item = dumper.represent_data(key)
        value_item = dumper.represent_data(value)
        node_item = yaml.MappingNode(u'tag:yaml.org,2002:map', [(key_item, value_item)],
                                     flow_style=False)
        values.append(node_item)
    return node


def represent_str(dumper, data):
    # borrowed from http://stackoverflow.com/a/33300001
    if len(data.splitlines()) > 1:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

def cli():
    import optparse
    parser = optparse.OptionParser(usage="%prog [options] source...",
                                   description="Merge YAML data from given files, dir or file glob",
                                   version="%" + "prog %s" % __version__,
                                   prog="yamlmerge")
    parser.add_option("--debug", dest="debug", action="store_true", default=False,
                      help="Enable debug logging [%default]")
    parser.add_option("--unique_list", action="store_true", default=False,
                      help="Enable unique lists [%default]")
    parser.add_option("--key_on", action="store", default='name',
                      help="Enable unique lists [%default]")
    options, args = parser.parse_args()
    if options.debug:
        logger = logging.getLogger()
        loghandler = logging.StreamHandler()
        loghandler.setFormatter(logging.Formatter('yamlmerge: %(levelname)s: %(message)s'))
        logger.addHandler(loghandler)
        logger.setLevel(logging.DEBUG)

    if not args:
        parser.error("Need at least one argument")
    try:
        yaml.SafeLoader.add_constructor(u'tag:yaml.org,2002:omap', construct_ordereddict)
        yaml.SafeDumper.add_representer(collections.OrderedDict, represent_ordereddict)
        yaml.SafeDumper.add_representer(str, represent_str)
        if six.PY2:
            yaml.SafeDumper.add_representer(unicode, represent_str)
        print(yaml.safe_dump(yaml_load(args, defaultdata={}, unique_list=options.unique_list, key_on=options.key_on),
                        indent=2, default_flow_style=False, canonical=False))
    except Exception as e:
        parser.error(e)

if __name__ == "__main__":
    cli()
