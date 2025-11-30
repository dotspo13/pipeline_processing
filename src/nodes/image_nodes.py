import time
import numpy as np
from PIL import Image, ImageFilter, ImageOps
from core.node import Node
from typing import Dict, Any, List

try:
    from skimage.measure import shannon_entropy
    HAS_SKIMAGE = True
except ImportError:
    HAS_SKIMAGE = False

class LoadImage(Node):
    INPUT_TYPES = {}
    OUTPUT_TYPES = {"image": "Image"}
    PARAMETERS = {"path": str}

    def execute(self, **inputs) -> Dict[str, Any]:
        path = self.params.get("path")
        print(f"Loading image from {path}")
        img = Image.open(path)
        img.load() 
        return {"image": img}

class SaveImage(Node):
    INPUT_TYPES = {"image": "Any"} # Supports Image or List[Image]
    OUTPUT_TYPES = {}
    PARAMETERS = {"path_prefix": str, "format": str}

    def execute(self, **inputs) -> Dict[str, Any]:
        data = inputs.get("image")
        prefix = self.params.get("path_prefix", "output")
        fmt = self.params.get("format", "png").lower()
        timestamp = int(time.time()*1000)
        
        if isinstance(data, list):
            print(f"Saving batch of {len(data)} images as {fmt}")
            for i, img in enumerate(data):
                filename = f"{prefix}_{timestamp}_{i}.{fmt}"
                print(f"  Saving {filename}")
                img.save(filename)
        elif data:
            filename = f"{prefix}_{timestamp}.{fmt}"
            print(f"Saving image to {filename}")
            data.save(filename)
        else:
             print("Nothing to save")
             
        return {}

class GaussianBlur(Node):
    INPUT_TYPES = {"image": "Image"}
    OUTPUT_TYPES = {"image": "Image"}
    PARAMETERS = {"radius": float}

    def execute(self, **inputs) -> Dict[str, Any]:
        img = inputs.get("image")
        radius = self.params.get("radius", 2.0)
        print(f"Applying Gaussian Blur with radius {radius}")
        result = img.filter(ImageFilter.GaussianBlur(radius))
        return {"image": result}

class Grayscale(Node):
    INPUT_TYPES = {"image": "Image"}
    OUTPUT_TYPES = {"image": "Image"}
    PARAMETERS = {}

    def execute(self, **inputs) -> Dict[str, Any]:
        img = inputs.get("image")
        print("Converting to Grayscale")
        result = ImageOps.grayscale(img)
        return {"image": result}

class BlendImages(Node):
    INPUT_TYPES = {"image_a": "Image", "image_b": "Image"}
    OUTPUT_TYPES = {"image": "Image"}
    PARAMETERS = {"alpha": float}

    def execute(self, **inputs) -> Dict[str, Any]:
        img_a = inputs.get("image_a")
        img_b = inputs.get("image_b")
        alpha = self.params.get("alpha", 0.5)
        
        print(f"Blending images with alpha {alpha}")
        
        img_b_resized = img_b.resize(img_a.size).convert(img_a.mode)
        result = Image.blend(img_a, img_b_resized, alpha)
        return {"image": result}

class ConvertToJPG(Node):
    INPUT_TYPES = {"image": "Image"}
    OUTPUT_TYPES = {"image": "Image"}
    PARAMETERS = {}

    def execute(self, **inputs) -> Dict[str, Any]:
        img = inputs.get("image")
        print("Converting to JPG format (RGB mode)")
        if img.mode != 'RGB':
            img = img.convert('RGB')
        return {"image": img}

class SliceImage(Node):
    INPUT_TYPES = {"image": "Image"}
    OUTPUT_TYPES = {"images": "List[Image]"}
    PARAMETERS = {"num_slices": int}

    def execute(self, **inputs) -> Dict[str, Any]:
        img = inputs.get("image")
        num_slices = self.params.get("num_slices", 2)
        print(f"Slicing image into {num_slices} horizontal strips")
        
        w, h = img.size
        slice_height = h // num_slices
        slices = []
        
        for i in range(num_slices):
            # box = (left, upper, right, lower)
            upper = i * slice_height
            lower = (i + 1) * slice_height if i < num_slices - 1 else h
            box = (0, upper, w, lower)
            slices.append(img.crop(box))
            
        return {"images": slices}

class StitchPanorama(Node):
    INPUT_TYPES = {"images": "List[Image]"}
    OUTPUT_TYPES = {"image": "Image"}
    PARAMETERS = {}

    def execute(self, **inputs) -> Dict[str, Any]:
        images = inputs.get("images")
        if not images:
            raise ValueError("No images to stitch")
            
        print(f"Stitching {len(images)} images")
        
        w = max(img.width for img in images)
        h = sum(img.height for img in images)
        
        result = Image.new('RGB', (w, h))
        y_offset = 0
        for img in images:
            result.paste(img, (0, y_offset))
            y_offset += img.height
            
        return {"image": result}

class CollectImages(Node):
    """
    Собирает изображения в список. 
    Может принимать как отдельные изображения, так и уже существующие списки (рекурсивно).
    Входы имеют тип Any, чтобы поддерживать и Image, и List[Image].
    """
    INPUT_TYPES = {
        "input_1": "Any", 
        "input_2": "Any"
    }
    OUTPUT_TYPES = {"images": "List[Image]"}
    PARAMETERS = {}

    def execute(self, **inputs) -> Dict[str, Any]:
        images = []
        for i in range(1, 3):
            key = f"input_{i}"
            val = inputs.get(key)
            
            if val is None:
                continue
                
            if isinstance(val, list):
                images.extend(val)
            else:
                images.append(val)
        
        print(f"Collecting {len(images)} images")
        return {"images": images}

class LoopMerge(Node):
    """
    Узел для организации циклов.
    - В первый раз выдает данные из входа 'initial'.
    - Во второй и последующие разы выдает данные из входа 'loop_back'.
    - Останавливается после заданного количества итераций.
    """
    INPUT_TYPES = {"initial": "Any", "loop_back": "Any"}
    OUTPUT_TYPES = {"value": "Any"}
    PARAMETERS = {"iterations": int}
    INPUT_STRATEGY = "ANY"

    def __init__(self, node_id, params=None):
        super().__init__(node_id, params)
        self.iteration = 0

    def execute(self, **inputs) -> Dict[str, Any]:
        max_iters = self.params.get("iterations", 5)
        
        if "initial" in inputs:
            print(f"LoopMerge: Resetting iteration count (received initial input)")
            self.iteration = 0
            
        if self.iteration >= max_iters:
            print(f"LoopMerge: Max iterations ({max_iters}) reached. Stopping propagation.")
            return {}

        val = None
        
        if "initial" in inputs:
            val = inputs["initial"]
            print(f"LoopMerge: Initial pass (iter {self.iteration + 1}/{max_iters})")
        elif "loop_back" in inputs:
            val = inputs["loop_back"]
            print(f"LoopMerge: Loop pass (iter {self.iteration + 1}/{max_iters})")
             
        self.iteration += 1
        return {"value": val}

class ImageQualityMetric(Node):
    INPUT_TYPES = {"image": "Image"}
    OUTPUT_TYPES = {"quality": "float"}
    PARAMETERS = {"metric": str} # "sharpness" or "entropy"

    def execute(self, **inputs) -> Dict[str, Any]:
        img = inputs.get("image")
        metric_name = self.params.get("metric", "sharpness")
        print(f"Calculating metric: {metric_name}")
        
        quality = 0.0
        
        if metric_name == "sharpness":

            gray = img.convert('L')

            edges = gray.filter(ImageFilter.FIND_EDGES)
            stat = ImageOps.grayscale(edges).getextrema()
            hist = edges.histogram()
            arr = np.array(gray)
            kernel = np.array([[0, -1, 0], [-1, 4, -1], [0, -1, 0]])
            quality = np.std(np.array(edges))
            
        elif metric_name == "entropy":
            if HAS_SKIMAGE:
                quality = shannon_entropy(np.array(img.convert('L')))
            else:
                print("Warning: skimage not found, returning 0 for entropy")
                quality = 0.0
                
        print(f"Quality ({metric_name}): {quality}")
        return {"quality": float(quality)}

class SelectBest(Node):
    INPUT_TYPES = {
        "image_1": "Image", "quality_1": "float",
        "image_2": "Image", "quality_2": "float"
    }
    OUTPUT_TYPES = {"image": "Image"}
    PARAMETERS = {}

    def execute(self, **inputs) -> Dict[str, Any]:
        q1 = inputs.get("quality_1", -1.0)
        q2 = inputs.get("quality_2", -1.0)
        img1 = inputs.get("image_1")
        img2 = inputs.get("image_2")
        
        print(f"Selecting best image: Q1={q1:.2f} vs Q2={q2:.2f}")
        
        if q1 >= q2:
            return {"image": img1}
        else:
            return {"image": img2}

NODE_REGISTRY = {
    "LoadImage": LoadImage,
    "SaveImage": SaveImage,
    "GaussianBlur": GaussianBlur,
    "Grayscale": Grayscale,
    "BlendImages": BlendImages,
    "ConvertToJPG": ConvertToJPG,
    "SliceImage": SliceImage,
    "StitchPanorama": StitchPanorama,
    "CollectImages": CollectImages,
    "ImageQualityMetric": ImageQualityMetric,
    "SelectBest": SelectBest,
    "LoopMerge": LoopMerge
}
