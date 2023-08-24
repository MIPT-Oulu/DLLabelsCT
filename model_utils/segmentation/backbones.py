"""
https://github.com/MIPT-Oulu/Collagen/blob/master/collagen/modelzoo/segmentation/backbones.py
"""

import torch
import torch.nn.functional as F
from torch import nn

from torchvision.models import resnet18, resnet34, resnet50

from model_utils.modules import Module


class ResNetBackbone(Module):

    """
    Extended implementation from https://github.com/qubvel/segmentation_models.pytorch

    """

    def __init__(self, n_classes, backbone_name='resnet50', dropout=None):
        super(ResNetBackbone, self).__init__()
        self.backbone_name = backbone_name
        if backbone_name == "resnet18":
            backbone = resnet18(weights=None)
        elif backbone_name == "resnet34":
            backbone = resnet34(weights=None)
        else:
            backbone = resnet50(weights=None)

        new_conv = nn.Conv2d(n_classes, 64, kernel_size=(7,7), stride=(2,2), padding=(3,3), bias=False)
        new_conv_param = torch.unsqueeze(backbone.conv1.weight[:, 0, :, :], 1)
        new_conv.weight = nn.parameter.Parameter(new_conv_param)

        self.layer0 = nn.Sequential(new_conv,
                                    backbone.bn1,
                                    nn.ReLU(inplace=True))

        self.layer1 = nn.Sequential(backbone.maxpool,
                                    backbone.layer1)

        self.layer2 = backbone.layer2
        self.layer3 = backbone.layer3
        self.layer4 = backbone.layer4

        self.dropout = dropout

        self.shape_dict = {'resnet18': (512, 256, 128, 64, 64),
                           'resnet34': (512, 256, 128, 64, 64),
                           'resnet50': (2048, 1024, 512, 256, 64)}

        self.dropout_on = False

    def switch_dropout(self):
        self.dropout_on = not self.dropout_on

    @property
    def output_shapes(self):
        return self.shape_dict[self.backbone_name]

    def forward(self, x):
        x0 = self.layer0(x)
        x1 = self.layer1(x0)
        if self.dropout is not None:
            x1_d = F.dropout(x1, self.dropout, training=self.dropout_on)
            x2 = self.layer2(x1_d)
        else:
            x2 = self.layer2(x1)

        if self.dropout is not None:
            x2_d = F.dropout(x2, self.dropout, training=self.dropout_on)
            x3 = self.layer3(x2_d)
        else:
            x3 = self.layer3(x2)

        if self.dropout is not None:
            x3_d = F.dropout(x3, self.dropout, training=self.dropout_on)
            x4 = self.layer4(x3_d)
        else:
            x4 = self.layer4(x3)

        return x0, x1, x2, x3, x4

    def get_features(self):
        pass

    def get_features_by_name(self, name: str):
        pass
