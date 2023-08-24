"""
https://github.com/MIPT-Oulu/Collagen/blob/master/collagen/core/_model.py
"""

from abc import abstractmethod

from typing import Tuple, Dict

import torch
import torch.nn as nn


class Module(nn.Module):
    """

    Generic building block, which assumes to have trainable parameters within it.

    This extension allows to group the layers and have an easy access to them via group names.

    """

    def __init__(self, input_shape=None, output_shape=None):

        super(Module, self).__init__()

        self.__param_groups = dict()

        self.optimize_cb = None

        self.__input_shape = input_shape

        self.__output_shape = output_shape

    def validate_input(self, x):

        if self.__input_shape is not None:

            if len(x.shape) != len(self.__input_shape):
                raise ValueError("Expect {}-dim input, but got {}".format(len(x.shape), len(self.__input_shape)))

            for i, d in enumerate(self.__input_shape):

                if d is not None and d != x.shape[i]:
                    raise ValueError(f"Expect dim {i} to be {d}, but got {x.shape[i]}")

    def validate_output(self, y):

        if self.__output_shape is not None:

            if len(y.shape) != len(self.__output_shape):
                raise ValueError("Expect {}-dim input, but got {}".format(len(y.shape), len(self.__output_shape)))

            for i, d in enumerate(self.__output_shape):

                if d is not None and d != y.shape[i]:
                    raise ValueError(f"Expect dim {i} to be {d}, but got {y.shape[i]}")

    def group_parameters(self, group: str or Tuple[str] or None = None,

                         name: str or None = None) -> Dict[str, torch.nn.Parameter or str]:

        """

        Returns an iterator through the parameters of the module from one or many groups.

        Also allows to retrieve a particular module from a group using its name.

        Parameters

        ----------

        group: str or Tuple[str] or None

            Parameter group names.

        name: str or Tuple[str] or None

            Name of the module from the group to be returned. Should be set to None

            if all the parameters from the group are needed. Alternatively, multiple modules

            from the group can be returned if it is a Tuple[str].

        Yields

        -------

        Parameters: Dict[str, torch.nn.Parameter or str]

            Dictionary of parameters. Allows to get all the parameters of submodules from multiple groups,

            or particular submodules' parameters from the given group. The returned dict has always three keys:

            params (used by optimizer), name (module name) and group name (name of the parameter groups). If name is not

            specified, it will be None.

        """

        if group is None:

            yield {'params': super(Module, self).parameters(), 'name': None, 'group_name': None}

        else:

            if name is None:

                if isinstance(group, str):
                    group = (group,)

                for group_name in group:
                    yield {'params': self.__param_groups[group_name],

                           'name': None,

                           'group_name': group_name}

            else:

                if not isinstance(group, str):
                    raise ValueError

                if isinstance(name, str):
                    name = (name,)

                for module_name in name:
                    yield {'params': self.__param_groups[group][module_name], 'name': module_name, 'group_name': group}

    def add_to(self, layer: torch.nn.Module, name: str, group_names: str or Tuple[str]):

        """

        Adds a layer with trainable parameters to one or several groups.

        Parameters

        ----------

        layer : torch.nn.Module

            The layer to be added to the group(s)

        name : str

            Name of the layer

        group_names: str Tuple[str]

            Group names.

        """

        if name is None or group_names is None:
            raise ValueError

        for group_name in group_names:

            if group_name not in self.__param_groups:
                self.__param_groups[group_name] = {}

            self.__param_groups[group_name][name] = layer.parameters()

    @abstractmethod
    def forward(self, *x):

        raise NotImplementedError

    @abstractmethod
    def get_features(self):

        raise NotImplementedError

    @abstractmethod
    def get_features_by_name(self, name: str):

        raise NotImplementedError

    def initialize(self):

        def init_weights(m):

            if isinstance(m, nn.Conv2d):

                nn.init.kaiming_normal_(m.weight, mode='fan_out', nonlinearity='relu')

            elif isinstance(m, nn.BatchNorm2d):

                nn.init.constant_(m.weight, 1)

                nn.init.constant_(m.bias, 0)

        self.apply(init_weights)

"""
https://github.com/MIPT-Oulu/Collagen/blob/master/collagen/modelzoo/modules/_modules.py
"""
class ConvBlock(Module):
    def __init__(self, ks, inp, out, stride=1, pad=1, activation='relu',
                 normalization='BN', bias=True):
        super(ConvBlock, self).__init__()
        layers = [nn.Conv2d(inp, out, kernel_size=ks, padding=pad, stride=stride, bias=bias), ]

        if normalization == 'BN':
            layers.append(nn.BatchNorm2d(out))
        elif normalization == 'IN':
            layers.append(nn.InstanceNorm2d(out))
        elif normalization is None:
            pass
        else:
            raise NotImplementedError('Not supported normalization type!')

        if activation == 'relu':
            layers.append(nn.ReLU(inplace=True))
        elif activation == 'selu':
            layers.append(nn.SELU(inplace=True))
        elif activation == 'elu':
            layers.append(nn.ELU(1, inplace=True))
        elif activation is None:
            pass
        else:
            raise NotImplementedError('Not supported activation type!')

        self.layers = nn.Sequential(*layers)

    def forward(self, x):
        return self.layers(x)

    def get_features(self):
        pass

    def get_features_by_name(self, name: str):
        pass
