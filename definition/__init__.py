# -*- coding: utf-8 -*-
# This file is part of the pymfony package.
#
# (c) Alexandre Quercia <alquerci@email.com>
#
# For the full copyright and license information, please view the LICENSE
# file that was distributed with this source code.
from __future__ import absolute_import;

import json;

from pymfony.component.system import Object;
from pymfony.component.system import Tool;
from pymfony.component.system.types import String;
from pymfony.component.system.types import Array;
from pymfony.component.system.types import OrderedDict;
from pymfony.component.system.oop import abstract;
from pymfony.component.system.oop import interface;
from pymfony.component.system.oop import final;
from pymfony.component.system.exception import InvalidArgumentException;
from pymfony.component.system.exception import RuntimeException;

from pymfony.component.config.definition.exception import ForbiddenOverwriteException;
from pymfony.component.config.definition.exception import DefinitionException;
from pymfony.component.config.definition.exception import InvalidConfigurationException;
from pymfony.component.config.definition.exception import InvalidTypeException;
from pymfony.component.config.definition.exception import UnsetKeyException;
from pymfony.component.config.definition.exception import DuplicateKeyException;

"""
"""


@interface
class NodeInterface(Object):
    """Common Interface among all nodes.

    In most cases, it is better to inherit from BaseNode instead of
    implementing this interface yourself.

    @author: Johannes M. Schmitt <schmittjoh@gmail.com>
    """
    def getName(self):
        """Returns the name of the node.

        @return: string
        """
        pass;

    def getPath(self):
        """Returns the path of the node.

        @return: string
        """
        pass;

    def isRequired(self):
        """Returns true when the node is required.

        @return: boolean
        """
        pass;

    def hasDefaultValue(self):
        """Returns true when the node has a default value.

        @return: Boolean
        """
        pass;

    def getDefaultValue(self):
        """Returns the default value of the node.

        @return: mixed

        @raise RuntimeException: if the node has no default value
        """
        pass;

    def normalize(self, value):
        """Normalizes the supplied value.

        @param value: mixed The value to normalize

        @return: mixed The normalized value
        """
        pass;

    def merge(self, leftSide, rightSide):
        """Merges two values together.

        @param leftSide: mixed
        @param rightSide: mixed

        @return: mixed The merged values
        """
        pass;

    def finalize(self, value):
        """Finalizes a value.

        @param value: mixed The value to finalize

        @return: mixed The finalized value
        """
        pass;


@interface
class ConfigurationInterface(Object):
    """Configuration interface

    @author Victor Berchet <victor@suumit.com>

    """
    def getConfigTreeBuilder(self):
        """Generates the configuration tree builder.

        @return: TreeBuilder The tree builder
        """
        pass;


@interface
class PrototypeNodeInterface(NodeInterface):
    """This interface must be implemented by nodes which can be used as prototypes.

    @author Johannes M. Schmitt <schmittjoh@gmail.com>

    """
    def setName(self, name):
        """Sets the name of the node.

        @param name: string The name of the node

        """
        pass;

class Processor(Object):
    """This class is the entry point for config
    normalization/merging/finalization.

    @author Johannes M. Schmitt <schmittjoh@gmail.com>

    """
    def process(self, configTree, configs):
        """Processes an array of configurations.

        @param configTree: NodeInterface The node tree describing
            the configuration
        @param configs: list An array of configuration items to process

        @return dict The processed configuration

        """
        assert isinstance(configTree, NodeInterface);
        assert isinstance(configs, list);

        currentConfig = dict();
        for config in configs:
            config = configTree.normalize(config);
            currentConfig = configTree.merge(currentConfig, config);

        return configTree.finalize(currentConfig);

    def processConfiguration(self, configuration, configs):
        """Processes an array of configurations.

        @param configuration: ConfigurationInterface The configuration class
        @param configs: list An array of configuration items to process

        @return dict The processed configuration

        """
        assert isinstance(configuration, ConfigurationInterface);
        assert isinstance(configs, list);

        return self.process(
            configuration.getConfigTreeBuilder().buildTree(),
            configs
        );

    @classmethod
    def normalizeConfig(cls, config, key, plural=None):
        """Normalizes a configuration entry.

        This method returns a normalize configuration array for
        a given key to remove the differences due to the original format
        (YAML and XML mainly).

        Here is an example.

        The configuration in XML:

        <twig:extension>twig.extension.foo</twig:extension>
        <twig:extension>twig.extension.bar</twig:extension>

        And the same configuration in YAML:

        extensions: ['twig.extension.foo', 'twig.extension.bar']

        @param config: dict A config array
        @param key: string The key to normalize
        @param plural: string The plural form of the key if it is irregular

        @return: list
        """
        assert isinstance(config, dict);
        key = str(key);
        plural = str(plural);

        if plural is None:
            plural = "{0}s".format(key);

        values = list();
        if plural in config:
            values = config[plural];
        elif key in config:
            if isinstance(config[key], list):
                values = config[key];
            else:
                # only one
                values = [config[key]];

        return list(values);


@abstract
class BaseNode(NodeInterface):
    """The base node class

    @author Johannes M. Schmitt <schmittjoh@gmail.com>

    """
    def __init__(self, name, parent=None):
        """Constructor.

        @param name: string The name of the node
        @param parent: NodeInterface The parent of this node

        @raise InvalidArgumentException: if the name contains a period.
        """
        assert isinstance(name, String);
        if parent is not None:
            assert isinstance(parent, NodeInterface);

        self._attributes = OrderedDict();

        self._name = name;
        self._parent = parent;
        self._normalizationClosures = list();
        self._finalValidationClosures = list();
        self._allowOverwrite = True;
        self._required = False;
        self._equivalentValues = list();

        if '.' in name:
            raise InvalidArgumentException('The name must not contain ".".');

    def setAttribute(self, key, value):
        self._attributes[key] = value;

    def hasAttribute(self, key):
        return key in self._attributes;

    def getAttribute(self, key, default=None):
        if self.hasAttribute(key):
            return self._attributes[key];
        return default;

    def getAttributes(self, key):
        return self._attributes;

    def setAttributes(self, attributes):
        assert isinstance(attributes, dict);
        self._attributes = attributes;

    def removeAttribute(self, key):
        return self._attributes.pop(key);

    def setInfo(self, info):
        """Sets an info message.

        @param info: string
        """
        self.setAttribute('info', info);

    def getInfo(self):
        """Returns info message.

        @return: string The info message.
        """
        return self.getAttribute('info');

    def setExample(self, example):
        """Sets the example configuration for this node.

        @param example: string|array
        """
        self.setAttribute('example', example);

    def getExample(self):
        """Retrieves the example configuration for this node.

        @return: string|array
        """
        return self.getAttribute('example');

    def addEquivalentValue(self, originalValue, equivalentValue):
        """Adds an equivalent value.

        @param originalValue: mixed
        @param equivalentValue: mixed
        """
        self._equivalentValues.append([originalValue, equivalentValue]);

    def setRequired(self, boolean):
        """Set this node as required.

        @param boolean: Boolean Required node
        """
        self._required = bool(boolean);

    def setAllowOverwrite(self, allow):
        """Sets if this node can be overridden.

        @param allow: Boolean
        """
        self._allowOverwrite = bool(allow);

    def setNormalizationClosures(self, closures):
        """Sets the closures used for normalization.

        @param closures: callable[] An array of Closures used for normalization
        """
        assert isinstance(closures, list);
        self._normalizationClosures = closures;

    def setFinalValidationClosures(self, closures):
        """Sets the closures used for final validation.

        @param closures: callable[] An array of Closures used 
            for final validation
        """
        assert isinstance(closures, list);
        self._finalValidationClosures = closures;

    def isRequired(self):
        """Checks if this node is required.

        @return Boolean

        """
        return self._required;

    def getName(self):
        """Returns the name of this node

        @return string The Node's name.

        """
        return self._name;

    def getPath(self):
        """Retrieves the path of this node.

        @return string The Node's path

        """
        path = self._name;
        if not self._parent is None:
            path = ".".join([self._parent.getPath(), self._name]);
        return path;

    @final
    def merge(self, leftSide, rightSide):
        """Merges two values together.

        @param leftSide:  mixed
        @param rightSide: mixed

        @return mixed The merged value

        @raise ForbiddenOverwriteException:

        """
        if not self._allowOverwrite:
            raise ForbiddenOverwriteException(
                'Configuration path "{0}" cannot be overwritten. You have to '
                'define all options for this path, and any of its sub-paths '
                'in one configuration section.'.format(self.getPath())
            );

        self._validateType(leftSide);
        self._validateType(rightSide);

        return self._mergeValues(leftSide, rightSide);

    @final
    def normalize(self, value):
        """Normalizes a value, applying all normalization closures.

        @param value: mixed Value to normalize.

        @return: mixed The normalized value.

        """
        # pre-normalize value
        value  = self._preNormalize(value);

        # run custom normalization closures
        for closure in self._normalizationClosures:
            value = closure(value);

        # replace value with their equivalent
        for data in self._equivalentValues:
            if data[0] == value:
                value = data[1];

        # validate type
        self._validateType(value);

        # normalize value
        return self._normalizeValue(value);

    def _preNormalize(self, value):
        """Normalizes the value before any other normalization is applied.

        @param value:

        @return: mixed The normalized array value

        """
        return value;

    @final
    def finalize(self, value):
        """Finalizes a value, applying all finalization closures.

        @param mixed $value The value to finalize

        @return mixed The finalized value

        @raise InvalidConfigurationException:

        """
        self._validateType(value);
        value = self._finalizeValue(value);

        # Perform validation on the final value if a closure has been set.
        # The closure is also allowed to return another value.
        for closure in self._finalValidationClosures:
            try:
                value = closure(value);
            except DefinitionException as correctEx:
                raise correctEx;
            except Exception as invalid:
                raise InvalidConfigurationException(
                    'Invalid configuration for path "{0}": {1}'
                    ''.format(self.getPath(), str(invalid)),
                    previous=invalid
                );
        return value;

    @abstract
    def _validateType(self, value):
        """Validates the type of a Node.

        @param value: mixed The value to validate

        @raise InvalidTypeException: When the value is invalid
        """
        pass;

    @abstract
    def _normalizeValue(self, value):
        """Normalizes the value.

        @param value: mixed The value to normalize.

        @return: mixed The normalized value
        """
        pass;

    @abstract
    def _mergeValues(self, leftSide, rightSide):
        """Merges two values together.

        @param leftSide: mixed
        @param rightSide: mixed

        @return: mixed
        """
        pass;

    @abstract
    def _finalizeValue(self, value):
        """Finalizes a value.

        @param value: The value to finalize

        @return: mixed The finalized value
        """
        pass;


class VariableNode(BaseNode, PrototypeNodeInterface):
    """This node represents a value of variable type in the config tree.

    This node is intended for values of arbitrary type.
    Any PYTHON type is accepted as a value.

    @author Jeremy Mikola <jmikola@gmail.com>

    """
    def __init__(self, name, parent=None):
        BaseNode.__init__(self, name, parent=parent);
        self._defaultValueSet = False;
        self._defaultValue = None;
        self._allowEmptyValue = True;

    def setDefaultValue(self, value):
        self._defaultValueSet = True;
        self._defaultValue = value;

    def hasDefaultValue(self):
        return self._defaultValueSet;

    def getDefaultValue(self):
        if Tool.isCallable(self._defaultValue):
            return eval(self._defaultValue)();
        else:
            return self._defaultValue;

    def setAllowEmptyValue(self, boolean):
        """Sets if this node is allowed to have an empty value.

        @param boolean: Boolean
        """
        self._allowEmptyValue = bool(boolean);

    def setName(self, name):
        self._name = name;

    def _validateType(self, value):
        pass;

    def _finalizeValue(self, value):
        if not self._allowEmptyValue and not value:
            ex = InvalidConfigurationException(
                'The path "{0}" cannot contain an empty value, but got {1}.'
                ''.format(self.getPath(), json.dumps(value))
            );
            ex.setPath(self.getPath());
            raise ex;
        return value;

    def _normalizeValue(self, value):
        return value;

    def _mergeValues(self, leftSide, rightSide):
        return rightSide;

class ScalarNode(VariableNode):
    """This node represents a scalar value in the config tree.

    The following values are considered scalars:
    * booleans
    * strings
    * null
    * integers
    * floats

    @author Johannes M. Schmitt <schmittjoh@gmail.com>

    """
    def _validateType(self, value):
        if not isinstance(value,(type(None),String,int,float,bool)) and \
            not value is None:
            ex = InvalidTypeException(
                'Invalid type for path "{0}". Expected scalar, but got {1}.'
                ''.format(self.getPath(), type(value).__name__)
            );
            ex.setPath(self.getPath());
            raise ex;

class BooleanNode(ScalarNode):
    """This node represents a Boolean value in the config tree.

    @author Johannes M. Schmitt <schmittjoh@gmail.com>

    """
    def _validateType(self, value):
        if not isinstance(value, bool):
            ex = InvalidTypeException(
                'Invalid type for path "{0}". Expected boolean, but got {1}.'
                ''.format(self.getPath(), type(value).__name__)
            );
            ex.setPath(self.getPath());
            raise ex;


class ArrayNode(BaseNode, PrototypeNodeInterface):
    """Represents an Array node in the config tree.

    @author Johannes M. Schmitt <schmittjoh@gmail.com>

    """
    def __init__(self, name, parent=None):
        """Constructor.

        @param name:   string        The Node's name
        @param parent: NodeInterface The node parent

        """
        BaseNode.__init__(self, name, parent=parent);

        self._xmlRemappings = list();
        self._children = OrderedDict();
        self._allowFalse = False;
        self._allowNewKeys = True;
        self._addIfNotSet = False;
        self._performDeepMerging = True;
        self._ignoreExtraKeys = None;
        self._normalizeKeys = True;

    def setNormalizeKeys(self, normalizeKeys):
        self._normalizeKeys = bool(normalizeKeys);

    def _preNormalize(self, value):
        """Normalizes keys between the different configuration formats.

        Namely, you mostly have foo_bar in YAML while you have foo-bar in XML.
        After running this method, all keys are normalized to foo_bar.

        If you have a mixed key like foo-bar_moo, it will not be altered.
        The key will also not be altered if the target key already exists.

        @param value: mixed

        @return dict The value with normalized keys

        """
        if not self._normalizeKeys or not isinstance(value, dict):
            return value;

        for k, v in value.items():
            if '-' in str(k):
                if not '_' in str(k):
                    normalizedKey = str(k).replace('-', '_');
                    if not normalizedKey in value:
                        value[normalizedKey] = v;
                        value.pop(k);

        return value;

    def getChildren(self):
        """Retrieves the children of this node.

        @return: dict The children
        """
        return self._children;

    def setXmlRemappings(self, xmlRemappings):
        """Sets the xml remappings that should be performed.

        @param xmlRemappings: an list of the form list(list(string, string))
        """
        self._xmlRemappings = list(xmlRemappings);

    def setAddIfNotSet(self, boolean):
        """Sets whether to add default values for this array if it has not
        been defined in any of the configuration files.

        @param boolean: Boolean
        """
        self._addIfNotSet = bool(boolean);

    def setAllowFalse(self, allow):
        """Sets whether false is allowed as value indicating that
        the array should be unset.

        @param allow: Boolean
        """
        self._allowFalse = bool(allow);

    def setAllowNewKeys(self, allow):
        """Sets whether new keys can be defined in subsequent configurations.

        @param allow: Boolean
        """
        self._allowNewKeys = bool(allow);

    def setPerformDeepMerging(self, boolean):
        """Sets if deep merging should occur.

        @param boolean: Boolean
        """
        self._performDeepMerging = bool(boolean);

    def setIgnoreExtraKeys(self, boolean):
        """Whether extra keys should just be ignore without an exception.

        @param boolean: Boolean To allow extra keys
        """
        self._ignoreExtraKeys = bool(boolean);

    def setName(self, name):
        """Sets the node Name.

        @param name: string The node's name
        """
        self._name = str(name);

    def hasDefaultValue(self):
        """Checks if the node has a default value.

        @return Boolean

        """
        return self._addIfNotSet;

    def getDefaultValue(self):
        """Retrieves the default value.

        @return: dict The default value

        @raise RuntimeException: if the node has no default value
        """
        if not self.hasDefaultValue():
            raise RuntimeException(
                'The node at path "{0}" has no default value.'
                ''.format(self.getPath())
            );

        default = dict();
        for name, child in self._children.items():
            if child.hasDefaultValue():
                default[name] = child.getDefaultValue();

        return default;


    def addChild(self, node):
        """Adds a child node.

        @param child: NodeInterface The child node to add

        @raise InvalidArgumentException: when the child node has no name
        @raise InvalidArgumentException: when the child node's name
            is not unique
        """
        assert isinstance(node, NodeInterface);

        name = node.getName();

        if not name:
            raise InvalidArgumentException('Child nodes must be named.');

        if name in self._children:
            raise InvalidArgumentException(
                'A child node named "{0}" already exists.'
                ''.format(name)
            );

        self._children[name] = node;


    def _finalizeValue(self, value):
        """Finalizes the value of this node.

        @param value: mixed

        @return: mixed The finalised value

        @raise UnsetKeyException:
        @raise InvalidConfigurationException: if the node doesn't have enough children

        """
        if value is False:
            raise UnsetKeyException(
                'Unsetting key for path "{0}", value: {1}'
                ''.format(self.getPath(), json.dumps(value))
            );

        for name, child in self._children.items():
            assert isinstance(child, NodeInterface);
            if not name in value:
                if child.isRequired():
                    ex = InvalidConfigurationException(
                        'The child node "{0}" at path "{1}" must be '
                        'configured.'.format(name, self.getPath())
                    );
                    ex.setPath(self.getPath());
                    raise ex;

                if child.hasDefaultValue():
                    value[name] = child.getDefaultValue();

                continue;

            try:
                value[name] = child.finalize(value[name]);
            except UnsetKeyException:
                value.pop(name);

        return value;

    def _validateType(self, value):
        """Validates the type of the value.

        @param value: mixed

        @raise InvalidTypeException:

        """
        if not isinstance(value, (dict, list)):
            if not self._allowFalse or value:
                ex = InvalidTypeException(
                    'Invalid type for path "{0}". Expected array, but got {1}'
                    ''.format(self.getPath(), type(value).__name__)
                );
                ex.setPath(self.getPath())
                raise ex;

    def _normalizeValue(self, value):
        """Normalizes the value.

        @param value: mixed The value to normalize

        @return: mixed The normalized value

        @raise InvalidConfigurationException:

        """
        if value is False:
            return value;

        if isinstance(value, list):
            value = Array.toDict(value);

        assert isinstance(value, dict);

        value = self._remapXml(value);
        normalized = dict();

        valueCopy = value.copy();

        for name, child in self._children.items():
            assert isinstance(child, NodeInterface)
            if name in valueCopy:
                normalized[name] = child.normalize(value[name]);
                valueCopy.pop(name);

        # if extra fields are present, throw exception
        if valueCopy and not self._ignoreExtraKeys:
            ex = InvalidConfigurationException(
                'Unrecognized options "{0}" under "{1}"'
                ''.format(", ".join(value.keys()), self.getPath())
            );
            ex.setPath(self.getPath());
            raise ex;

        return normalized;

    def _remapXml(self, value):
        """Remaps multiple singular values to a single plural value.

        @param value: cict The source values

        @return: dict The remapped values
        """
        assert isinstance(value, dict);

        for singular, plural in self._xmlRemappings:
            if not singular in value:
                continue;

            value[plural] = Processor.normalizeConfig(value, singular, plural);
            value.pop(singular);

        return value;


    def _mergeValues(self, leftSide, rightSide):
        """Merges values together.

        @param leftSide:  mixed The left side to merge.
        @param rightSide: mixed The right side to merge.

        @return: mixed The merged values

        @rasie InvalidConfigurationException:
        @rasie RuntimeException:

        """
        if rightSide is False:
            # if this is still false after the last config has been merged the
            # finalization pass will take care of removing this key entirely
            return False;

        if not leftSide or not self._performDeepMerging:
            return rightSide;

        if isinstance(rightSide, list):
            rightSide = Array.toDict(rightSide);

        for k, v in rightSide.items():
            # no conflict
            if k not in leftSide:
                if not self._allowNewKeys:
                    ex = InvalidConfigurationException(
                        'You are not allowed to define new elements for path '
                        '"{0}". Please define all elements for this path in '
                        'one config file. If you are trying to overwrite an '
                        'element, make sure you redefine it with the same '
                        'name.'.format(self.getPath())
                    );
                    ex.setPath(self.getPath());
                    raise ex;

                leftSide[k] = v;
                continue;

            if k not in self._children:
                raise RuntimeException(
                    'merge() expects a normalized config array.'
                );

            leftSide[k] = self._children[k].merge(leftSide[k], v);

        return leftSide;


class PrototypedArrayNode(ArrayNode):
    """Represents a prototyped Array node in the config tree.

    @author Johannes M. Schmitt <schmittjoh@gmail.com>

    """
    def __init__(self, name, parent=None):
        """Constructor.

        @param name:   string        The Node's name
        @param parent: NodeInterface The node parent

        """
        ArrayNode.__init__(self, name, parent=parent);
        self._prototype = None;
        self._keyAttribute = None;
        self._removeKeyAttribute = None;
        self._minNumberOfElements = 0;
        self._defaultValue = dict();
        self._defaultChildren = dict(); # dict

    def setMinNumberOfElements(self, numder):
        """Sets the minimum number of elements that a prototype based node
        must contain. By default this is zero, meaning no elements.

        @param numder: int

        """
        self._minNumberOfElements = int(numder);

    def setKeyAttribute(self, attribute, remove=True):
        """Sets the attribute which value is to be used as key.

        This is useful when you have an indexed array that should be an
        associative array. You can select an item from within the array
        to be the key of the particular item. For example, if "id" is the
        "key", then:

        {
            {'id': "my_name", 'foo': "bar"},
        }

        becomes

        {
            'my_name': {'foo': "bar"},
        };

        If you'd like "'id' => 'my_name'" to still be present in the resulting
        array, then you can set the second argument of this method to false.

        @param attribute: string The name of the attribute which value is
            to be used as a key
        @param remove: boolean Whether or not to remove the key

        """
        self._keyAttribute = str(attribute);
        self._removeKeyAttribute = bool(remove);

    def getKeyAttribute(self):
        """Retrieves the name of the attribute which value should be used as
        key.

        @return: string The name of the attribute
        """
        return self._keyAttribute;

    def setDefaultValue(self, value):
        """Sets the default value of this node.

        @param value: dict

        @raise InvalidArgumentException: if the default value is not an array
        """
        if isinstance(value, list):
            value = Array.toDict(value);
        if not isinstance(value, dict):
            raise InvalidArgumentException(
                '{0}: the default value of an array node has to be an array.'
                ''.format(self.getPath())
            );

        self._defaultValue = value;

    def hasDefaultValue(self):
        """Checks if the node has a default value.

        @return Boolean

        """
        return True;

    def setAddChildrenIfNoneSet(self, children=None):
        """Adds default children when none are set.

        @param children: integer|string|dict|null The number of
            children|The child name|The children names to be added
        """
        if children is None:
            children = ['defaults'];
        elif isinstance(children, int) and children > 0:
            children = list(range(1, children+1));
        elif isinstance(children, String):
            children = [children];

        if isinstance(children, list):
            children = Array.toDict(children);

        assert isinstance(children, dict);
        self._defaultChildren = children;

    def getDefaultValue(self):
        """Retrieves the default value.

        The default value could be either explicited or derived from the
        prototype default value.

        @return array The default value

        """
        if self._defaultChildren:
            if self._prototype.hasDefaultValue():
                default = self._prototype.getDefaultValue();
            else:
                default = dict();

            defaults = dict();
            values = list(self._defaultChildren.values());
            for i in range(len(values)):
                if self._keyAttribute is None:
                    key = i;
                else:
                    key = values[i];
                defaults[key] = default;

            return defaults;

        return self._defaultValue;

    def setPrototype(self, node):
        """Sets the node prototype.

        @param node: PrototypeNodeInterface
        """
        assert isinstance(node, PrototypeNodeInterface);
        self._prototype = node;

    def getPrototype(self):
        """Retrieves the prototype

        @return: PrototypeNodeInterface The prototype
        """
        return self._prototype;

    def addChild(self, node):
        """Disable adding concrete children for prototyped nodes.

        @param node: NodeInterface The child node to add

        @raise DefinitionException: Always
        """
        assert isinstance(node, NodeInterface);

        raise DefinitionException(
            'A prototyped array node can not have concrete children.'
        );

    def _finalizeValue(self, value):
        """Finalizes the value of this node.

        @param value: mixed

        @return mixed The finalized value

        @raise UnsetKeyException:
        @raise InvalidConfigurationException: if the node doesn't have enough
            children

        """
        if value is False:
            raise UnsetKeyException(
                'Unsetting key for path "%s", value: %s'
                ''.format(self.getPath(), json.dumps(value))
            )

        assert isinstance(value, dict);

        for k, v in value.items():
            self._prototype.setName(k);
            try:
                value[k] = self._prototype.finalize(v);
            except UnsetKeyException:
                value.pop(k);

        if len(value) < self._minNumberOfElements:
            ex = InvalidConfigurationException(
                'The path "{0}" should have at least {1} element(s) defined.'
                ''.format(self.getPath(), self._minNumberOfElements)
            );
            ex.setPath(self.getPath());
            raise ex;

        return value;

    def _normalizeValue(self, value):
        """Normalizes the value.

        @param value: mixed The value to normalize

        @return mixed The normalized value

        @raise InvalidConfigurationException:
        @raise DuplicateKeyException:

        """
        if value is False:
            return value;

        if isinstance(value, list):
            value = Array.toDict(value);

        assert isinstance(value, dict);

        value = self._remapXml(value);

        isAssoc = list(value.keys()) != list(range(len(value)));
        normalized = dict();

        i = -1;
        for k, v in value.items():
            i += 1;

            if self._keyAttribute is not None and isinstance(v, (dict, list)):
                if isinstance(v, list):
                    v = Array.toDict(v);

                if self._keyAttribute not in v \
                    and isinstance(k, int) \
                    and not isAssoc:
                    ex = InvalidConfigurationException(
                        'The attribute "{0}" must be set for path "{1}".'
                        ''.format(self._keyAttribute, self.getPath())
                    );
                    ex.setPath(self.getPath());
                    raise ex;
                elif self._keyAttribute in v:
                    k = v[self._keyAttribute];

                    # remove the key attribute when required
                    if self._removeKeyAttribute:
                        del v[self._keyAttribute];

                    # if only "value" is left
                    if 1 == len(v) and 'value' in v:
                        v = v['value'];

                if k in normalized:
                    ex = DuplicateKeyException(
                        'Duplicate key "{0}" for path "{1}".'
                        ''.format(k, self.getPath())
                    );
                    ex.setPath(self.getPath());
                    raise ex;

            self._prototype.setName(k);
            if not self._keyAttribute is None or isAssoc:
                normalized[k] = self._prototype.normalize(v);
            else:
                normalized[i] = self._prototype.normalize(v);

        return normalized;

    def _mergeValues(self, leftSide, rightSide):
        """Merges values together.

        @param leftSide:  mixed The left side to merge.
        @param rightSide: mixed The right side to merge.

        @return mixed The merged values

        @raise InvalidConfigurationException:
        @raise RuntimeException:

        """
        if rightSide is False:
            # if this is still false after the last config has been merged the
            # finalization pass will take care of removing this key entirely
            return False;

        if not leftSide or not self._performDeepMerging:
            return rightSide;

        if isinstance(leftSide, list):
            leftSide = Array.toDict(leftSide);

        if isinstance(rightSide, list):
            rightSide = Array.toDict(rightSide);

        i = -1;
        for k, v in rightSide.items():
            i += 1;
            # prototype, and key is irrelevant, so simply append the element
            if self._keyAttribute is None:
                # dict: append
                index = 0;
                while index in leftSide:
                    index += 1;
                leftSide[index] = v;
                continue;

            # no conflict
            if k not in leftSide:
                if not self._allowNewKeys:
                    ex = InvalidConfigurationException(
                        'You are not allowed to define new elements for path '
                        '"{0}". Please define all elements for this path in '
                        'one config file. If you are trying to overwrite an '
                        'element, make sure you redefine it with the same '
                        'name.'.format(self.getPath())
                    );
                    ex.setPath(self.getPath());
                    raise ex;

                leftSide[k] = v;
                continue;

            self._prototype.setName(k);
            leftSide[k] = self._prototype.merge(leftSide[k], v);

        return leftSide;



class EnumNode(ScalarNode):
    """Node which only allows a finite set of values.

    @author Johannes M. Schmitt <schmittjoh@gmail.com>

    """


    def __init__(self, name, parent = None, values = None):
        if values is None:
            values = list();
        assert isinstance(values, list);
        if parent:
            assert isinstance(parent, NodeInterface);

        self.__values = None;

        values = Array.uniq(values);
        if (len(values) <= 1) :
            raise InvalidArgumentException('values must contain at least two distinct elements.');


        ScalarNode.__init__(self, name, parent);
        self.__values = values;


    def getValues(self):

        return self.__values;


    def _finalizeValue(self, value):

        value = ScalarNode._finalizeValue(self, value);

        if value not in self.__values :
            ex = InvalidConfigurationException(
                'The value {0} is not allowed for path "{1}". Permissible '
                'values: {2}'.format(
                json.dumps(value),
                self.getPath(),
                ', '.join(map(json.dumps, self.__values))));
            ex.setPath(self.getPath());

            raise ex;


        return value;




class NumericNode(ScalarNode):
    """This node represents a numeric value in the config tree

    @author David Jeanmonod <david.jeanmonod@gmail.com>

    """


    def __init__(self, name, parent = None, minValue = None, maxValue = None):
        if parent is not None:
            assert isinstance(parent, NodeInterface);

        self._min = None;
        self._max = None;

        ScalarNode.__init__(self, name, parent);
        self._min = minValue;
        self._max = maxValue;


    def _finalizeValue(self, value):

        value = ScalarNode._finalizeValue(self, value);

        errorMsg = None;
        if (self._min and value < self._min) :
            errorMsg = (
                'The value {0} is too small for path "{1}". Should be '
                'greater than: {2}'.format(value, self.getPath(), self._min)
            );

        if (self._max and value > self._max) :
            errorMsg = (
                'The value {0} is too big for path "{1}". Should be less '
                'than: {2}'.format(value, self.getPath(), self._max)
            );

        if errorMsg :
            ex = InvalidConfigurationException(errorMsg);
            ex.setPath(self.getPath());
            raise ex;


        return value;


class IntegerNode(NumericNode):
    """This node represents an integer value in the config tree.

    @author Jeanmonod David <david.jeanmonod@gmail.com>

    """

    def _validateType(self, value):

        if ( not isinstance(value, int)) or value is False or value is True:
            ex = InvalidTypeException(
                'Invalid type for path "{0}". Expected int, but got {1}.'
                ''.format(self.getPath(), type(value))
            );
            ex.setPath(self.getPath());

            raise ex;



class FloatNode(NumericNode):
    """This node represents a float value in the config tree.

    @author Jeanmonod David <david.jeanmonod@gmail.com>

    """

    def _validateType(self, value):

        # Integers are also accepted, we just cast them
        if (isinstance(value, int)) and value is not True and value is not False:
            value = float(value);


        if ( not isinstance(value, float)) :
            ex = InvalidTypeException(
                'Invalid type for path "{0}". Expected float, but got {1}.'
                ''.format(self.getPath(), type(value))
            );
            ex.setPath(self.getPath());

            raise ex;




class ReferenceDumper(Object):
    """Dumps a reference configuration for the given configuration/node instance.

    Currently, only YML format is supported.

    @author Kevin Bond <kevinbond@gmail.com>

    """

    def __init__(self):
        self.__reference = None;

    def dump(self, configuration):
        assert isinstance(configuration, ConfigurationInterface);

        return self.dumpNode(configuration.getConfigTreeBuilder().buildTree());


    def dumpNode(self, node):
        assert isinstance(node, NodeInterface);

        self.__reference = '';
        self.__writeNode(node);
        ref = self.__reference;
        self.__reference = None;

        return ref;


    def __writeNode(self, node, depth = 0):
        """
        @param NodeInterface node
        @param integer       depth

        """
        assert isinstance(node, NodeInterface);

        comments = list();
        default = '';
        defaultArray = None;
        children = None;
        example = node.getExample();

        # defaults
        if (isinstance(node, ArrayNode)) :
            children = node.getChildren();

            if (isinstance(node, PrototypedArrayNode)) :
                prototype = node.getPrototype();

                if (isinstance(prototype, ArrayNode)) :
                    children = prototype.getChildren();


                # check for attribute as key
                key = node.getKeyAttribute();
                if (key) :
                    keyNode = ArrayNode(key, node);
                    keyNode.setInfo('Prototype');

                    # add children
                    for childNode in children.values():
                        keyNode.addChild(childNode);

                    children = {key: keyNode};



            if ( not children) :
                defaultArray = node.getDefaultValue();
                if (node.hasDefaultValue() and len(defaultArray)) :
                    default = '';
                elif not isinstance(example, (list, dict)) :
                    default = '[]';


        else :
            default = '~';

            if (node.hasDefaultValue()) :
                default = node.getDefaultValue();

                if (True is default) :
                    default = 'true';
                elif (False is default) :
                    default = 'false';
                elif (None is default) :
                    default = '~';
                elif isinstance(default, (list, dict)) :
                    defaultArray = node.getDefaultValue();
                    if (node.hasDefaultValue() and len(defaultArray)) :
                        default = '';
                    elif not isinstance(example, (list, dict)) :
                        default = '[]';





        # required?
        if (node.isRequired()) :
            comments.append('Required');


        # example
        if example and  not isinstance(example, (list, dict)) :
            comments.append('Example: '+example);


        if default != '':
            default = ' '+default;
        else:
            default = '';
        default = str(default);

        if comments:
            comments = '# '+', '.join(comments);
        else:
            comments = '';

        text = '{0:20} {1} {2}'.format(node.getName()+':', default, comments).rstrip(' ');

        info = node.getInfo()
        if info :
            self.__writeLine('');
            # indenting multi-line info
            info = info.replace('\n', ('\n{0:>'+str(depth * 4)+'}# ').format(' '));
            self.__writeLine('# '+info, depth * 4);


        self.__writeLine(text, depth * 4);

        # output defaults
        if (defaultArray) :
            self.__writeLine('');

            if len(defaultArray) > 1:
                message = 'Defaults';
            else:
                message = 'Default';

            self.__writeLine('# '+message+':', depth * 4 + 4);

            self.__writeArray(defaultArray, depth + 1);


        if (isinstance(example, (list, dict))) :
            self.__writeLine('');

            if len(example) > 1:
                message = 'Examples'
            else:
                message = 'Example';

            self.__writeLine('# '+message+':', depth * 4 + 4);

            self.__writeArray(example, depth + 1);


        if (children) :
            for childNode in children.values():
                self.__writeNode(childNode, depth + 1);




    def __writeLine(self, text, indent = 0):
        """Outputs a single config reference line

        @param string text
        @param int    indent

        """

        indent = len(text) + indent;
        formatString = '{0:>'+str(indent)+'}';

        self.__reference += formatString.format(text)+"\n";


    def __writeArray(self, array, depth):
        assert isinstance(array, (list, dict));

        isIndexed = False;
        if isinstance(array, dict):
            for key in array.keys():
                if not isinstance(key, int):
                    isIndexed = False;
                    break;
        else:
            isIndexed = True;
            array = Array.toDict(array);

        for key, value in array.items():
            if isinstance(value, (list, dict)) :
                val = '';
            else :
                val = value;


            if (isIndexed) :
                self.__writeLine('- '+val, depth * 4);
            else :
                self.__writeLine('{0:20} {1}'.format( key+':', val), depth * 4);


            if isinstance(value, (list, dict)) :
                self.__writeArray(value, depth + 1);
