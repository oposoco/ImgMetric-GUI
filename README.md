
**Description**

This is a small and fast script i made to calculate SSIMULACRA 2 and Butteraugli metrics on images. Further informations on the metrics can be found inside the program. It features both a single file mode and a batch mode. Each one gets further functionalities:

<img width="300" height="250" alt="215409" src="https://github.com/user-attachments/assets/3d8e4546-98e6-498f-8b6e-d52e827a8bae" />
<img width="300" height="250" alt="215423" src="https://github.com/user-attachments/assets/57aac6cc-f697-4ed1-aa76-40a06ceaa9ae" />
<br><br>

*   **Single mode:** has an optimizer with RD-Curve, to properly calculate for each codec what settings are the most efficient and where the diminishing returns lie. Also several difference maps to provide a basic view of errors caused by the compression; the errors are standardized and a gain was applied. They are meant as a complement to the heatmap produced by Butteraugli itself.
*   **Batch mode:** is made for folders containing a high amount of images to calculate. Individual scores can be saved into CSVs and a premade plot is available.

  
<img width="600" height="400" alt="ff" src="https://github.com/user-attachments/assets/f502300a-bea9-47f2-ab65-e9ff0f40458b" />
<br><br>
<img width="312" height="337" alt="215744" src="https://github.com/user-attachments/assets/2043f181-0a98-4a8b-a1a1-0582011d95bb" />



***

**Requirements**

*   Python

**Optional Dependencies**

*   `tkinterdnd2` for drag and drop functionalities
*   `matplotlib` for the optimizer, the difference maps, and the batch plot
*   `pillow` for the difference maps

```bash
pip install tkinterdnd2 matplotlib pillow
```

**Installation**

Put the python script inside the `libjxl` static folder (where `ssimulacra2.exe`, `butteraugli_main.exe`, and `djxl.exe` are located).
Tested with jxl-x64-windows-static.zip v0.11.1 https://github.com/libjxl/libjxl/releases

***

### **Update v1.0**

**Various changes, Most notably:**


*   **Recursive Batch Analysis:** Batch folder analysis now supports subfolder scanning. It maps files based on relative paths (ensure the internal folder structures match).

*   **High-Density Carpet Plot:** Added a new Carpet Plot for batch results. This provides a clearer visual overview of quality trends across several thousand images (ideal for manga, comics, or large frame datasets).

*   **Pillow Conversion:** Given the limited format support of libjxl binaries, the script now uses Pillow to convert images to PNG before analysis for formats like WebP, TIF, and others.


