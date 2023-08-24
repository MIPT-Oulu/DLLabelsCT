"""
https://github.com/MIPT-Oulu/Collagen/blob/master/collagen/modelzoo/segmentation/_model_wrapper.py
"""

from torch import nn

from model_utils.modules import Module
from model_utils.segmentation import backbones
from model_utils.segmentation import constants
from model_utils.decoders import FPNDecoder
from model_utils.decoders import UNetDecoder


class EncoderDecoder(Module):
    def __init__(self, n_outputs, backbone: str or nn.Module, decoder: str or nn.Module,
                 decoder_normalization='BN', spatial_dropout=None, bayesian_dropout=None,
                 unet_activation='relu', unet_width=32):
        super(EncoderDecoder, self).__init__()
        if isinstance(backbone, str):
            if backbone in constants.allowed_encoders:
                if 'resnet' in backbone:
                    backbone = backbones.ResNetBackbone(backbone, dropout=bayesian_dropout)
                else:
                    ValueError('Cannot find the implementation of the backbone!')
            else:
                raise ValueError('This backbone name is not in the list of allowed backbones!')

        if isinstance(decoder, str):
            if decoder in constants.allowed_decoders:
                if decoder == 'FPN':
                    decoder = FPNDecoder(encoder_channels=backbone.output_shapes,
                                         pyramid_channels=256, segmentation_channels=128,
                                         final_channels=n_outputs, spatial_dropout=spatial_dropout,
                                         normalization=decoder_normalization,
                                         bayesian_dropout=bayesian_dropout)
                elif decoder == 'UNet':
                    decoder = UNetDecoder(encoder_channels=backbone.output_shapes,
                                          width=unet_width, activation=unet_activation,
                                          final_channels=n_outputs,
                                          spatial_dropout=spatial_dropout,
                                          normalization=decoder_normalization)

        decoder.initialize()

        self.backbone = backbone
        self.decoder = decoder

    def forward(self, x):
        features = self.backbone(x)
        return self.decoder(features)

    def switch_dropout(self):
        """
        Has effect only if the model supports monte-carlo dropout inference.

        """
        self.backbone.switch_dropout()
        self.decoder.switch_dropout()

    def get_features(self):
        pass

    def get_features_by_name(self, name: str):
        pass
