import enum
import json
from collections import Generator

from django.utils import six
from django.utils.encoding import smart_text
from django.utils.xmlutils import SimplerXMLGenerator


class _GeneratorListWrapper(list):
    def __init__(self, gen):
        self.gen = gen
        super().__init__()

    def __iter__(self):
        return iter(self.gen)

    def __len__(self):
        return 1


def iterdump_json(file, data):
    if isinstance(data, Generator):
        data = _GeneratorListWrapper(data)
    for chunk in json.JSONEncoder().iterencode(data):
        file.write(chunk.encode('utf-8'))


def _to_xml(xml, data):
    item_tag_name = 'list-item'
    if isinstance(data, (list, tuple)):
        for item in data:
            xml.startElement(item_tag_name, {})
            _to_xml(xml, item)
            xml.endElement(item_tag_name)
    elif isinstance(data, dict):
        for key, value in six.iteritems(data):
            xml.startElement(key, {})
            _to_xml(xml, value)
            xml.endElement(key)
    elif data is None:
        # Don't output any value
        pass
    else:
        xml.characters(smart_text(data))


def iterdump_xml(file, data):
    if isinstance(data, Generator):
        data = _GeneratorListWrapper(data)

    root_tag_name = 'root'

    xml = SimplerXMLGenerator(file, 'utf-8')
    xml.startDocument()
    xml.startElement(root_tag_name, {})

    _to_xml(xml, _GeneratorListWrapper(data))

    xml.endElement(root_tag_name)
    xml.endDocument()


class Format(enum.Enum):
    xml = 'xml'
    json = 'json'


_AVAILABLE_FORMATS = {
    Format.json: iterdump_json,
    Format.xml: iterdump_xml
}


def iterdump(format_type, file, data):
    format_type = Format(format_type)
    return _AVAILABLE_FORMATS[format_type](file, data)
