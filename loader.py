# -*- coding: utf-8 -*-
# This file is part of the pymfony package.
#
# (c) Alexandre Quercia <alquerci@email.com>
#
# For the full copyright and license information, please view the LICENSE
# file that was distributed with this source code.
from __future__ import absolute_import;

from pymfony.component.system import Object;
from pymfony.component.system.oop import interface;
from pymfony.component.system.oop import abstract;

from pymfony.component.config import FileLocatorInterface;
from pymfony.component.config.exception import FileLoaderImportCircularReferenceException;
from pymfony.component.config.exception import FileLoaderLoadException;

"""
"""

@interface
class LoaderResolverInterface(Object):
    """LoaderResolverInterface selects a loader for a given resource.

    @author Fabien Potencier <fabien@symfony.com>

    """
    def resolve(self, resource, resourceType = None):
        """Returns a loader able to load the resource.

        @param resource:     mixed
        @param resourceType: string The resource type

        @return: LoaderInterface|false A LoaderInterface instance
        """
        pass;


@interface
class LoaderInterface(Object):
    """LoaderInterface is the interface implemented by all loader classes.

    @author Fabien Potencier <fabien@symfony.com>

    """
    def load(self, resource, resourceType = None):
        """Loads a resource.

        @param resource: mixed
        @param resourceType: string The resource type
        """
        pass;

    def supports(self, resource, resourceType = None):
        """Returns true if this class supports the given resource.

        @param resource:     mixed
        @param resourceType: string The resource type

        @return: Boolean
        """
        pass;

    def getResolver(self):
        """Gets the loader resolver.

        @return: LoaderResolverInterface A LoaderResolverInterface instance
        """
        pass;

    def setResolver(self, resolver):
        """Sets the loader resolver.

        @param resolver: LoaderResolverInterface A LoaderResolverInterface instance
        """
        pass;


class LoaderResolver(LoaderResolverInterface):
    """LoaderResolver selects a loader for a given resource.

    A resource can be anything (e.g. a full path to a config file or a Closure).
    Each loader determines whether it can load a resource and how.

    @author Fabien Potencier <fabien@symfony.com>

    """
    def __init__(self, loaders = None):
        """Constructor.

        @param LoaderInterface[] $loaders An array of loaders

        """
        if loaders is None:
            loaders = list();
        self.__loaders = list();
        for loader in list(loaders):
            self.addLoader(loader);

    def resolve(self, resource, resourceType = None):
        """Returns a loader able to load the resource.

        @param mixed $resource A resource
        @param string $type The resource type

        @return LoaderInterface|False A LoaderInterface instance

        """
        for loader in self.__loaders:
            if loader.supports(resource, resourceType):
                return loader;

        return False;

    def addLoader(self, loader):
        """Add a Loader

        @param loader: LoaderInterface A LoaderInterface instance

        """
        assert isinstance(loader, LoaderInterface);
        self.__loaders.append(loader);
        loader.setResolver(self); 

    def getLoaders(self):
        """Returns the registered loaders.

        @return: LoaderInterface[] An array of LoaderInterface instances

        """
        return self.__loaders;


@abstract
class Loader(LoaderInterface):
    """Loader is the abstract class used by all built-in loaders.

    @author Fabien Potencier <fabien@symfony.com>

    """
    def __init__(self):
        self._resolver = None;

    def getResolver(self):
        """Gets the loader resolver.

        @return LoaderResolverInterface A LoaderResolverInterface instance

        """
        return self._resolver;

    def setResolver(self, resolver):
        """Sets the loader resolver.

        @param resolver: LoaderResolverInterface A LoaderResolverInterface instance

        """
        assert isinstance(resolver, LoaderResolverInterface);
        self._resolver = resolver;

    def imports(self, resource, resourceType=None):
        """Imports a resource.

        @param resource: mixed
        @param resourceType: string The resource type

        @return: mixed

        """
        return self.resolve(resource).load(resource, resourceType);

    def resolve(self, resource, resourceType=None):
        """Finds a loader able to load an imported resource.

        @param resource: mixed
        @param resourceType: string The resource type

        @return: LoaderInterface A LoaderInterface instance

        @raise FileLoaderLoadException: if no loader is found

        """
        if self.supports(resource, resourceType):
            return self;

        if self._resolver is None:
            loader = False;
        else:
            loader = self._resolver.resolve(resource, resourceType);

        if loader is False:
            raise FileLoaderLoadException(resource);

        return loader;


class DelegatingLoader(Loader):
    """DelegatingLoader delegates loading to other loaders using a loader resolver.

    This loader acts as an array of LoaderInterface objects - each having
    a chance to load a given resource (handled by the resolver)

    @author Fabien Potencier <fabien@symfony.com>

    """
    def __init__(self, resolver):
        """Constructor.

        @param resolver: LoaderResolverInterface A LoaderResolverInterface instance

        """
        assert isinstance(resolver, LoaderResolverInterface);
        self._resolver = resolver;

    def load(self, resource, resourceType=None):
        """Loads a resource.

        @param resource: mixed
        @param resourceType: string The resource type

        @return: mixed

        @raise FileLoaderLoadException: if no loader is found.

        """
        loader = self._resolver.resolve(resource, resourceType);
        if loader is False:
            raise FileLoaderLoadException(resource);
        return loader.load(resource, resourceType);

    def supports(self, resource, resourceType=None):
        return False if False is self._resolver.resolve(resource, resourceType) else True;


@abstract
class FileLoader(Loader):
    """FileLoader is the abstract class used by all built-in loaders that
    are file based.

    @author Fabien Potencier <fabien@symfony.com>

    """
    _loading = dict();

    def __init__(self, locator):
        """Constructor.

        @param locator: FileLocatorInterface A FileLocatorInterface instance

        """
        assert isinstance(locator, FileLocatorInterface);
        self.__currentDir = None;

        self._locator = locator;

    def setCurrentDir(self, directory):
        self.__currentDir = directory;

    def getLocator(self):
        return self._locator;

    def imports(self, resource, resourceType=None, 
                ignoreErrors=False, sourceResource=None):
        """Imports a resource.

        @param resource: mixed
        @param resourceType: string The resource type
        @param ignoreErrors: Boolean Whether to ignore import errors or not
        @param sourceResource: string The original resource
            importing the new resource

        @return: mixed

        @raise FileLoaderLoadException:
        @raise FileLoaderImportCircularReferenceException:

        """
        try:
            loader = self.resolve(resource, resourceType);
            if isinstance(loader, FileLoader) and \
                not self.__currentDir is None:
                resource = self._locator.locate(resource, self.__currentDir);
            if resource in self._loading.keys():
                raise FileLoaderImportCircularReferenceException(
                    list(self._loading.keys())
                );

            self._loading[resource] = True;
            ret = loader.load(resource, resourceType);
            del self._loading[resource];

            return ret;
        except FileLoaderImportCircularReferenceException as e:
            raise e;
        except Exception as e:
            if not ignoreErrors:
                # prevent embedded imports from nesting multiple exceptions
                if isinstance(e, FileLoaderLoadException):
                    raise e;
                raise FileLoaderLoadException(resource, sourceResource, 0, e);
