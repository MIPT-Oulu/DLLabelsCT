import torch
import numpy as np

from model_utils.decoders import FPNDecoder
from model_utils.decoders import UNetDecoder
from model_utils.segmentation import EncoderDecoder
from model_utils.segmentation.backbones import ResNetBackbone


def segmentation(models, stack, device, indexes, class_amount, window):

    with torch.no_grad():
        window.progressBar.show()
        progress = 0
        average_preds = torch.zeros((stack.shape[0], class_amount, stack.shape[1], stack.shape[2])).to(device)
        stack = stack / 256.
        stack -= stack.mean()
        stack /= stack.std()
        stack = stack / 255

        model_name = str(models[0])
        model = init_segmentation_model(model_name, class_amount, device=device)

        for model_index, model_weights in enumerate(models):
            model.load_state_dict(torch.load(model_weights, map_location=device)["model"])
            model = model.to(device)
            model.eval()
            for i in range(stack.shape[0]):
                if i not in indexes and indexes != []:
                    progress += 1
                    continue
                progress += 1
                window.progressBar.setValue(int(progress / (len(models)*stack.shape[0])*100))
                image = stack[i, :, :]
                image = np.expand_dims(image, axis=(0, 1))
                image = torch.from_numpy(image).to(device).float()
                out = model(image)
                th = 0.3
                preds = out.gt(th)
                average_preds[i, :, :, :] += preds[0, :, :, :]
                
        tensor_pred = average_preds / len(models)
        tensor_pred = tensor_pred.gt(0.5)
        if class_amount == 1:
            numpy_pred = tensor_pred[:, 0, :, :].cpu().detach().numpy()
        else:
            numpy_pred = tensor_pred.cpu().detach().numpy()
        torch.cuda.empty_cache()
        return numpy_pred


def init_segmentation_model(model_name, n_classes, device='cuda'):

    if "resnet18" in model_name.lower():
        resnet_num = "resnet18"
    elif "resnet34" in model_name.lower():
        resnet_num = "resnet34"
    elif "resnet50" in model_name.lower():
        resnet_num = "resnet50"
    else:
        raise NotImplementedError

    resnet_backbone = ResNetBackbone(n_classes, resnet_num)
    if 'unet' in model_name.lower():
        mdl = EncoderDecoder(2, resnet_backbone, UNetDecoder(resnet_backbone.shape_dict[resnet_num], final_channels=n_classes))
    elif 'fpn' in model_name.lower():
        mdl = EncoderDecoder(2, resnet_backbone, FPNDecoder(resnet_backbone.shape_dict[resnet_num], final_channels=n_classes))
    else:
        raise NotImplementedError

    mdl = mdl.to(device)

    return mdl
