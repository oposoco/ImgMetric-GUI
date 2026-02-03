
**Description**

This is a small and fast script i made to calculate SSIMULACRA 2 and Butteraugli metrics on images. Further informations on the metrics can be found inside the program. It features both a single file mode and a batch mode. Each one gets further functionalities:


<img width="300" height="250" alt="064524" src="https://github.com/user-attachments/assets/d333bb1b-6594-48b4-bb24-a7292b5b8762" />
<img width="300" height="250" alt="064538" src="https://github.com/user-attachments/assets/a450944e-ff4d-4deb-960d-cacdaad04034" />
<br><br>

*   **Single mode:** has an optimizer with RD-Curve, to properly calculate for each codec what settings are the most efficient and where the diminishing returns lie. Also several difference maps to provide a basic view of errors caused by the compression; the errors are standardized and a gain was applied. They are meant as a complement to the heatmap produced by Butteraugli itself.
*   **Batch mode:** is made for folders containing a high amount of images to calculate. Individual scores can be saved into CSVs and a premade plot is available.
  

<img width="600" height="400" alt="3f" src="https://github.com/user-attachments/assets/7ece840d-c837-4be1-b580-65124b2eccb0" />
<br><br>
<img width="310" height="318" alt="064008" src="https://github.com/user-attachments/assets/7ed782c2-573b-4215-a2b3-28ac5ce655fd" />



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


