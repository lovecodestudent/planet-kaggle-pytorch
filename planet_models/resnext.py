"""
    A re-implementation of ResNeXT. All the blocks are of bottleneck type.
    The code follows the style of resnet.py in pytorch vision model.
"""
import torch
from torch.nn import *
from torch.nn import functional as F


class Bottleneck(Module):
    expansion = 4
    """Type C in the paper"""
    def __init__(self, inplanes, planes, width, cardinality, stride, downsample=None, activation_fn=ELU):
        """
        Params:
            inplanes: # of input channels
            planes: # of output channels
            width: # of channels in the bottleneck layer
            cardinality: # of convolution groups
            stride: convolution stride
            downsample: convolution operation to increase the width of the output
            activation_fn: activation function
        """
        super(Bottleneck, self).__init__()
        d = width * cardinality
        # reduce width
        self.conv1 = Conv2d(inplanes, d, kernel_size=1, stride=1, padding=0, bias=False)
        self.bn1 = BatchNorm2d(d)
        # group convolution
        self.conv2 = Conv2d(d, d, kernel_size=3,  groups=cardinality, stride=stride, padding=1, bias=False)
        self.bn2 = BatchNorm2d(d)
        # increase width
        self.conv3 = Conv2d(d, planes, kernel_size=1, stride=1, padding=0, bias=False)
        self.bn3 = BatchNorm2d(planes)

        self.downsample = downsample
        self.activation = activation_fn

    def forward(self, x):
        residual = x
        # reduce width
        out = self.conv1(x)
        out = self.bn1(out)
        out = self.activation(out, inplace=True)

        # group conv
        out = self.conv2(out)
        out = self.bn2(out)
        out = self.activation(out, inplace=True)

        # increase width
        out = self.conv3(out)
        out = self.bn3(out)

        # identity mapping or projection
        if self.downsample is not None:
            residual = self.downsample(residual)

        out += residual
        out = self.activation(out, inplace=True)
        return out


class ResNeXT(Module):
    def __init__(self, block, depths, num_classes, cardinality=32, activation_fn=ELU):
        super(ResNeXT, self).__init__()
        self.inplanes = 64
        self.cardinality = cardinality
        self.widen_factor = self.inplanes * block.expansion // self.cardinality
        self.conv1 = Conv2d(3, 64, kernel_size=7, stride=2, padding=3, bias=False)
        self.bn1 = BatchNorm2d(64)
        self.activation = activation_fn(inplace=True)
        self.maxpool = MaxPool2d(kernel_size=3, stride=2, padding=1)
        self.stage1 = self._make_layers(block, 64, 'stage1', depths[0])
        self.stage2 = self._make_layers(block, 128, 'stage2', depths[1], stride=2)
        self.stage3 = self._make_layers(block, 256, 'stage3', depths[2], stride=2)
        self.stage4 = self._make_layers(block, 512, 'stage4', depths[3], stride=2)
        self.avgpool = AvgPool2d(7)
        self.fc = Linear(block.expansion*512, num_classes)

    def _make_layers(self, block, planes, name, blocks, stride=1):
        """
        Params
            block: type of the ResNeXT block
            planes: input channels
            blocks: number of residual blocks in this stage
            name: name of this stage
            stride: stride for the first residual block of each stage
        Returns
            A sequential module representing the stage
        """
        downsample = None
        if stride != 1 or self.inplanes != planes * block.expansion:
            downsample = Sequential(
                Conv2d(self.inplanes, planes * block.expansion, kernel_size=1, stride=stride, padding=0, bias=False),
                BatchNorm2d(planes * block.expansion)
            )

        stage = Sequential()
        stage.add_module('{}_block1'.format(name), block(self.inplanes, planes,  self.width, self.cardinality, stride,
                                                         downsample, self.activation))
        self.inplanes = planes * block.expansion
        for i in range(1, blocks):
            stage.add_module('{}_block{}'.format(name, i+1), block(self.inplanes, planes, self.width, self.cardinality,
                                                                 stride, activation_fn=self.activation))
        print(self.width, planes)
        self.width = self.cardinality * block.expansion // planes
        return stage

    def forward(self, x):
        pass


if __name__ == '__main__':
    model = ResNeXT(Bottleneck, [2, 3, 2, 3], 10)
    print(model)