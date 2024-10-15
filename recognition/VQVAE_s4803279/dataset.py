"""
This file contains the data loader for preprocessing the data.

The data is augmented and then packed into loaders for the model.
"""
import torch
from torch.utils.data import Dataset, DataLoader
import nibabel as nib
import numpy as np
import os
from tqdm import tqdm


def to_channels(arr: np.ndarray, dtype=np.uint8) -> np.ndarray:
    channels = np.unique(arr)
    res = np.zeros(arr.shape + (len(channels),), dtype=dtype)
    for c in channels:
        c = int(c)
        res[..., c:c+1][arr == c] = 1
    return res


def load_data_2D(imageNames, normImage=False, categorical=False, dtype=np.float32, getAffines=False, early_stop=False):
    affines = []

    num = len(imageNames)
    first_case = nib.load(imageNames[0]).get_fdata(caching='unchanged')
    if len(first_case.shape) == 3:
        first_case = first_case[:,:,0]

    if categorical:
        first_case = to_channels(first_case, dtype=dtype)
        rows, cols, channels = first_case.shape
        images = np.zeros((num, rows, cols, channels), dtype=dtype)
    else:
        rows, cols = first_case.shape
        images = np.zeros((num, rows, cols), dtype=dtype)

    for i, inName in enumerate(tqdm(imageNames)):
        niftiImage = nib.load(inName)
        inImage = niftiImage.get_fdata(caching='unchanged')
        affine = niftiImage.affine
        if len(inImage.shape) == 3:
            inImage = inImage[:,:,0]
        inImage = inImage.astype(dtype)
        if normImage:
            inImage = (inImage - inImage.mean()) / inImage.std()
        if categorical:
            inImage = to_channels(inImage, dtype=dtype)
            images[i,:,:,:] = inImage
        else:
            images[i,:,:] = inImage

        affines.append(affine)
        if i > 20 and early_stop:
            break

    if getAffines:
        return images, affines
    else:
        return images


class VQVAENIfTIDataset(Dataset):
    def __init__(self, data_dir, transform=None, normImage=True, categorical=False):
        self.data_dir = data_dir
        self.transform = transform
        self.normImage = normImage
        self.categorical = categorical
        self.file_list = [os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.endswith('.nii.gz')]
        self.images = load_data_2D(self.file_list, normImage=self.normImage, categorical=self.categorical)


    def __len__(self):
        return len(self.images)


    def __getitem__(self, idx):
        image = self.images[idx]

        # Convert to PyTorch tensor
        image_tensor = torch.from_numpy(image).float()

        # Add channel dimension if it's a 2D image
        if image_tensor.dim() == 2:
            image_tensor = image_tensor.unsqueeze(0)

        if self.transform:
            image_tensor = self.transform(image_tensor)

        return image_tensor


def create_nifti_data_loaders(data_dir, batch_size, num_workers=4, normImage=True, categorical=False):
    dataset = VQVAENIfTIDataset(data_dir, normImage=normImage, categorical=categorical)
    data_loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=num_workers)
    return data_loader
