"""
Synthetic UI Generator Module

Generates randomized web layouts, forms, and interactions for training/evaluation.
"""

from evaluation.synthetic_ui.generator import SyntheticUIGenerator
from evaluation.synthetic_ui.labeling import UILabelingHelper
from evaluation.synthetic_ui.export import DatasetExporter

__all__ = ["SyntheticUIGenerator", "UILabelingHelper", "DatasetExporter"]
