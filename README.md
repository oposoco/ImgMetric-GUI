
<h1 align="center"><img width="32" height="30" alt="2026 - 11_51PM" src="https://github.com/user-attachments/assets/de2edb29-74a8-4f4e-b734-0a8e9e666c0a" alt="Icon" style="vertical-align:middle; margin-right:10px;" /> <span>IMAGE METRIC TOOL</span></h1>

<p align="center"><img width="602" height="571" alt="045632" src="https://github.com/user-attachments/assets/de303619-0e42-45ef-9cb1-3ddf00f4bf19" /><p>

***
**Description**


This script provides a high-performance GUI for comparing image compression quality using SSIMULACRA 2 and Butteraugli metrics. Further information on the metrics can be found inside the program. It features both a single file mode and a batch mode. Each one gets further functionalities:

<h3 align="left">Single Mode</h3>

**Optimizer with RD-Curve:** Properly calculate for each codec what settings are the most efficient and where the diminishing returns lie. 

**Difference Maps:** 8 maps that provide a view of errors caused by compression; the errors are standardized and a gain is applied. They are meant as a complement to the heatmap produced by Butteraugli itself.

<h3 align="left">Batch Mode</h3>

Made for folders containing a high amount of images. Individual scores can be saved into CSVs. It features 7 advanced plots to identify the efficiency and distribution of various codecs and their settings.

<p align="center"><img width="675" height="561" alt="050204" src="https://github.com/user-attachments/assets/3746dc36-cbe7-4fdb-9356-042ad58340e4" /><p>

***

**Requirements**

*   Python

**Optional Dependencies**

```bash
pip install tkinterdnd2 matplotlib pillow numpy opencv-python scikit-image scipy
```
*   `tkinterdnd2` for drag and drop functionalities.
*   `matplotlib` for the optimizer and all the premade plots.
*   `pillow` for better format support and difference maps.
*   `opencv-python` & `scikit-image` for the difference maps.
*   `scipy` for the batch premade plots.

<br>

**Installation**

Put the python script inside the `libjxl` static folder (where `ssimulacra2.exe`, `butteraugli_main.exe`, and `djxl.exe` are located).
Tested with jxl-x64-windows-static.zip v0.11.1 https://github.com/libjxl/libjxl/releases

***

### **Update v2.0**

**UI Redesign:** Complete interface overhaul to a minimal and modern dark theme.

**New** difference maps for a total of 9 specialized views to better identify introduced artifacts.

**Advanced Analytics:** New "Optimizer" and "Plot+" tools in batch mode, featuring 7 plot types to identify codec efficiency and quality distribution.

### **Update v1.0**

**Recursive Batch Analysis:** Batch folder analysis now supports subfolder scanning. It maps files based on relative paths (ensure the internal folder structures match).

**High-Density Carpet Plot:** Provides a visual overview of quality trends across several thousand images.

**Pillow Conversion:** The script now uses Pillow to convert images to PNG before analysis for formats like WebP, TIF, and others not natively supported by the binaries.

