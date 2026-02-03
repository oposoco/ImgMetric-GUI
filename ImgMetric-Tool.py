import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import subprocess
import os
import re
import threading
import statistics
import csv
from concurrent.futures import ThreadPoolExecutor

# --- OPTIONAL DEPENDENCIES ---
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_SUPPORT = True
except ImportError:
    DND_SUPPORT = False

try:
    # UPDATED IMPORTS FOR NEW GRAPHS
    import matplotlib.pyplot as plt
    import matplotlib.colors as mcolors
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    from matplotlib.figure import Figure 
    from mpl_toolkits.axes_grid1.inset_locator import inset_axes
    import numpy as np
    from PIL import Image, ImageChops, ImageFilter, ImageOps
    MPL_SUPPORT = True
except ImportError:
    MPL_SUPPORT = False

# --- CONFIGURATION ---
BIN_DIR = os.path.dirname(os.path.abspath(__file__))
SSIM_EXE = os.path.join(BIN_DIR, "ssimulacra2.exe")
BUTTER_EXE = os.path.join(BIN_DIR, "butteraugli_main.exe")
DJXL_EXE = os.path.join(BIN_DIR, "djxl.exe") 
INTENSITY = "80"

# Fallback for Window class if dnd is missing
BaseClass = TkinterDnD.Tk if DND_SUPPORT else tk.Tk

# =============================================================================
#  CLASS: OPTIMIZER (RD-CURVE) - [UPDATED & FIXED]
# =============================================================================
class OptimizerWindow(tk.Toplevel):
    def __init__(self, parent, ssim_exe):
        super().__init__(parent)
        self.title("Codec Optimizer (RD-Curve)")
        self.geometry("800x700")
        self.ssim_exe = ssim_exe
        
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text="1. Select Original Image:").pack(anchor="w")
        self.ent_orig = ttk.Entry(main_frame)
        self.ent_orig.pack(fill="x", pady=(0, 5))
        if DND_SUPPORT:
            self.ent_orig.drop_target_register(DND_FILES)
            self.ent_orig.dnd_bind('<<Drop>>', lambda e: self.drop_handler(e, self.ent_orig))
            
        ttk.Button(main_frame, text="Browse Original", command=self.set_orig).pack(anchor="e")

        ttk.Label(main_frame, text="2. Add Encoded Versions:").pack(anchor="w", pady=(10, 0))
        self.list_box = tk.Listbox(main_frame, height=8)
        self.list_box.pack(fill="x", pady=5)
        
        if DND_SUPPORT:
            self.list_box.drop_target_register(DND_FILES)
            self.list_box.dnd_bind('<<Drop>>', self.drop_list_handler)
        
        btn_box = ttk.Frame(main_frame)
        btn_box.pack(fill="x")
        ttk.Button(btn_box, text="Add Files", command=self.add_enc).pack(side="left")
        ttk.Button(btn_box, text="Clear List", command=self.clear_enc).pack(side="right")

        ttk.Separator(main_frame, orient="horizontal").pack(fill="x", pady=15)
        
        self.btn_run = ttk.Button(main_frame, text="GENERATE RD-CURVE PLOT", command=self.run_analysis)
        self.btn_run.pack(fill="x", pady=10)
        
        self.log = scrolledtext.ScrolledText(main_frame, height=10, font=("Consolas", 9))
        self.log.pack(fill="both", expand=True)

    def drop_handler(self, event, widget):
        path = event.data
        if path.startswith('{') and path.endswith('}'): path = path[1:-1]
        widget.delete(0, tk.END); widget.insert(0, path)

    def drop_list_handler(self, event):
        raw = event.data
        files = re.findall(r'\{.*?\}|\S+', raw)
        for f in files:
            clean = f.strip('{}')
            if os.path.exists(clean): self.list_box.insert(tk.END, clean)

    def set_orig(self):
        f = filedialog.askopenfilename()
        if f: self.ent_orig.delete(0, tk.END); self.ent_orig.insert(0, f)

    def add_enc(self):
        files = filedialog.askopenfilenames()
        if files:
            for f in files: self.list_box.insert(tk.END, f)

    def clear_enc(self):
        self.list_box.delete(0, tk.END)

    def get_bpp(self, filepath, width, height):
        if width == 0 or height == 0: return 0
        size_bytes = os.path.getsize(filepath)
        size_bits = size_bytes * 8
        return size_bits / (width * height)

    def run_analysis(self):
        orig = self.ent_orig.get().strip().strip('"')
        encoded_files = self.list_box.get(0, tk.END)

        if not orig or not encoded_files:
            messagebox.showerror("Error", "Need Original and at least one Encoded file.")
            return
        
        self.btn_run.config(state="disabled")
        self.log.delete(1.0, tk.END)
        self.log.insert(tk.END, "Starting analysis...\n")
        
        threading.Thread(target=self._process, args=(orig, encoded_files)).start()

    def _process(self, orig, enc_list):
        data_points = []
        w, h = 0, 0
        
        try:
            # Helper to get size
            if orig.lower().endswith('.jxl') and os.path.exists(DJXL_EXE):
                 subprocess.run([DJXL_EXE, orig, orig+".tmp_size.png"], capture_output=True)
                 if os.path.exists(orig+".tmp_size.png"):
                     with Image.open(orig+".tmp_size.png") as img: w, h = img.size
                     os.remove(orig+".tmp_size.png")
            elif MPL_SUPPORT:
                try:
                    with Image.open(orig) as img: w, h = img.size
                except: pass
            
            for enc in enc_list:
                res = subprocess.run([self.ssim_exe, orig, enc], capture_output=True, text=True)
                out_text = res.stdout + res.stderr
                floats = [float(x) for x in re.findall(r"[-+]?(?:\d*\.\d+|\d+)", out_text)]
                
                score = -1.0
                if floats:
                    candidates = [x for x in floats if 0 <= x <= 110]
                    if candidates: score = candidates[-1]
                    else: score = floats[-1]
                
                if score != -1.0:
                    bpp = self.get_bpp(enc, w, h)
                    name = os.path.basename(enc)
                    data_points.append({'name': name, 'bpp': bpp, 'score': score})
                    self.log_safe(f"Processed: {name} | BPP: {bpp:.3f} | Score: {score:.4f}\n")

            data_points.sort(key=lambda x: x['bpp'])
            self.after(0, lambda: self.show_results(data_points))

        except Exception as e:
            self.log_safe(f"Critical Error: {str(e)}\n")
            self.after(0, lambda: self.btn_run.config(state="normal"))

    def log_safe(self, text):
        self.after(0, lambda: self.log.insert(tk.END, text))

    def format_name(self, filename):
        base, ext = os.path.splitext(filename)
        if len(base) > 8:
            return f"{base[:3]}...{base[-3:]}{ext}"
        return filename

    def show_results(self, data):
        self.btn_run.config(state="normal")
        if not data or not MPL_SUPPORT: return

        bpps = [d['bpp'] for d in data]
        scores = [d['score'] for d in data]
        names = [self.format_name(d['name']) for d in data]

        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Plot: Black Solid Line, Smaller Points (s=80)
        ax.plot(bpps, scores, linestyle='-', color='black', alpha=0.5, zorder=1)
        sc = ax.scatter(bpps, scores, c=scores, cmap='Spectral', vmin=50, vmax=100, s=80, edgecolor='k', zorder=2)
        
        # Labels
        for i, txt in enumerate(names):
            ax.annotate(txt, (bpps[i], scores[i]), xytext=(5, -12), textcoords='offset points', fontsize=9, fontweight='bold')

        ax.set_title("Rate-Distortion Efficiency")
        ax.set_xlabel("Bits Per Pixel (BPP)")
        ax.set_ylabel("SSIMULACRA 2 Score")
        ax.grid(True, linestyle='--', alpha=0.3)
        ax.set_ylim(50, 105)
        
        # --- MARGIN ADJUSTMENT (EQUALIZED) ---
        if bpps:
            min_b = min(bpps)
            max_b = max(bpps)
            spread = max_b - min_b
            if spread == 0: spread = 0.1 
            margin = spread * 0.15
            
            left_lim = max(0, min_b - margin)
            right_lim = max_b + margin
            
            ax.set_xlim(left=left_lim, right=right_lim)

        # --- LEGEND (Adjusted 0.1 Vertical) ---
        axins = inset_axes(ax, width="25%", height="2%", loc='lower right', 
                           bbox_to_anchor=(0.0, 0.1, 0.97, 1), 
                           bbox_transform=ax.transAxes,
                           borderpad=0)
        
        cbar = plt.colorbar(sc, cax=axins, orientation='horizontal')
        cbar.ax.tick_params(labelsize=8)
        cbar.outline.set_linewidth(0.5)

        # MANUAL LAYOUT to avoid tight_layout warning
        fig.subplots_adjust(left=0.12, bottom=0.12, right=0.95, top=0.92)
        
        plt.show()

# =============================================================================
#  CLASS: VISUAL LAB (3 MAPS) - [NEW & ISOLATED]
# =============================================================================
class VisualLabWindow(tk.Toplevel):
    def __init__(self, parent, orig_path, dist_path):
        super().__init__(parent)
        self.title("Diff. Maps (Fixed Gain x10)")
        self.geometry("1400x600") 
        
        self.orig_img = self.load_image_safe(orig_path)
        self.dist_img = self.load_image_safe(dist_path)
        
        if not self.orig_img or not self.dist_img:
            messagebox.showerror("Error", "Could not load images. Check if djxl.exe is present.")
            self.destroy()
            return

        if self.orig_img.size != self.dist_img.size:
            self.dist_img = self.dist_img.resize(self.orig_img.size)

        ttk.Label(self, text="Artifact Maps (Synchronized Zoom | Darker = Better Quality)").pack(pady=5)

        # Use OO Figure to isolate from pyplot global state (Fixes bug)
        self.fig = Figure(figsize=(15, 5))
        self.fig.subplots_adjust(left=0.01, right=0.99, bottom=0.01, top=0.95, wspace=0.02)
        
        self.ax1 = self.fig.add_subplot(131)
        self.ax2 = self.fig.add_subplot(132)
        self.ax3 = self.fig.add_subplot(133)
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().pack(side="top", fill="both", expand=True)
        
        toolbar = NavigationToolbar2Tk(self.canvas, self)
        toolbar.update()
        
        self.generate_maps()

    def load_image_safe(self, path):
        if path.lower().endswith(".jxl"):
            if not os.path.exists(DJXL_EXE): return None
            tmp = path + ".tmpview.png"
            subprocess.run([DJXL_EXE, path, tmp], capture_output=True)
            if os.path.exists(tmp):
                try:
                    img = Image.open(tmp).convert("RGB")
                    img.load(); return img
                finally:
                    try: os.remove(tmp)
                    except: pass
        try: return Image.open(path).convert("RGB")
        except: return None

    def generate_maps(self):
        img1 = self.orig_img
        img2 = self.dist_img
        
        arr1 = np.array(img1).astype(float)
        arr2 = np.array(img2).astype(float)
        
        GAIN = 10.0 

        # 1. Amplified Difference
        diff_abs = np.abs(arr1 - arr2) * GAIN
        diff_abs = np.clip(diff_abs, 0, 255).astype(np.uint8)
        map_diff = Image.fromarray(diff_abs) 

        # 2. Texture/Edge Loss
        e1 = img1.filter(ImageFilter.FIND_EDGES)
        e2 = img2.filter(ImageFilter.FIND_EDGES)
        arr_e1 = np.array(e1).astype(float)
        arr_e2 = np.array(e2).astype(float)
        diff_edge = np.abs(arr_e1 - arr_e2) * GAIN
        diff_edge = np.clip(diff_edge, 0, 255).astype(np.uint8)
        map_edge = Image.fromarray(diff_edge)

        # 3. Chroma Error
        yuv1 = img1.convert("YCbCr")
        yuv2 = img2.convert("YCbCr")
        _, cb1, cr1 = yuv1.split()
        _, cb2, cr2 = yuv2.split()
        
        def get_diff_channel(c1, c2):
            a1 = np.array(c1).astype(float)
            a2 = np.array(c2).astype(float)
            d = np.abs(a1 - a2) * GAIN
            d = np.clip(d, 0, 255).astype(np.uint8)
            return Image.fromarray(d)

        d_cb = get_diff_channel(cb1, cb2)
        d_cr = get_diff_channel(cr1, cr2)
        blank = Image.new("L", img1.size, 0)
        map_chroma = Image.merge("RGB", (d_cr, d_cb, blank)) 

        # Plot
        self.ax1.imshow(map_diff)
        self.ax1.set_title("General Pixel Diff")
        self.ax1.axis("off")

        self.ax2.imshow(map_edge)
        self.ax2.set_title("Edge/Texture Loss")
        self.ax2.axis("off")

        self.ax3.imshow(map_chroma)
        self.ax3.set_title("Color Error")
        self.ax3.axis("off")

        self.ax1.sharex(self.ax2)
        self.ax1.sharey(self.ax2)
        self.ax2.sharex(self.ax3)
        self.ax2.sharey(self.ax3)
        
        self.canvas.draw()

# =============================================================================
#  MAIN GUI - [RESTORED ORIGINAL & INTEGRATED NEW WINDOWS]
# =============================================================================
class MetricToolGUI(BaseClass):
    def __init__(self):
        super().__init__()
        self.title("Image Metric Tool")
        self.geometry("900x750")
        self.current_heatmap = None
        self.last_results = [] 

        # --- STYLES ---
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure("Contrast.Horizontal.TProgressbar", 
                        troughcolor='black', 
                        background='white', 
                        bordercolor='black', 
                        lightcolor='white', 
                        darkcolor='white')

        # Tabs
        self.tab_control = ttk.Notebook(self)
        self.tab_single = ttk.Frame(self.tab_control)
        self.tab_batch = ttk.Frame(self.tab_control)
        
        self.tab_control.add(self.tab_single, text='Single Image Analysis')
        self.tab_control.add(self.tab_batch, text='Batch Folder Analysis')
        self.tab_control.pack(expand=1, fill="both")

        self.setup_single_tab()
        self.setup_batch_tab()

        if not os.path.exists(SSIM_EXE) or not os.path.exists(BUTTER_EXE):
            messagebox.showwarning("Binaries Missing", 
                                   f"Could not find executables.\nEnsure 'ssimulacra2.exe' and 'butteraugli_main.exe' are in:\n{BIN_DIR}")

    # ==========================================
    # COMMON: DRAG AND DROP
    # ==========================================
    def drop_handler(self, event, entry_widget):
        path = event.data
        if path.startswith('{') and path.endswith('}'):
            path = path[1:-1]
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, path)

    # ==========================================
    # COMMON: INFO WINDOW
    # ==========================================
    def open_info_window(self):
        info_win = tk.Toplevel(self)
        info_win.title("Metric Information")
        info_win.geometry("700x900")
        
        txt = scrolledtext.ScrolledText(info_win, wrap=tk.WORD, padx=15, pady=15, 
                                        font=("Consolas", 10), bg="#f0f0f0")
        txt.pack(fill="both", expand=True)
        
        txt.tag_config("h1", font=("Segoe UI", 14, "bold"), foreground="#2c3e50")
        txt.tag_config("h2", font=("Segoe UI", 11, "bold"), foreground="#e67e22")
        txt.tag_config("bold", font=("Segoe UI", 10, "bold"))
        txt.tag_config("green", foreground="green")
        txt.tag_config("red", foreground="red")
        txt.tag_config("magenta", foreground="magenta")

        # 1. SSIMULACRA 2
        txt.insert(tk.END, "SSIMULACRA 2\n\n", "h1")
        desc_ssim = (
            "SSIMULACRA2 is a visual fidelity metric based on the concept of the multi-scale structural "
            "similarity index measure (MS-SSIM), computed in a perceptually relevant color space, "
            "adding two other (asymmetric) error maps, and aggregating using two different norms. "
            "It is currently the most reputable visual quality metric according to its correlation "
            "with subjective results, and is considered a very robust means of comparing encoders. "
            "It is debatable whether Butteraugli is better for very high fidelity, but SSIMULACRA2 "
            "is considered the best for medium/low fidelity comparisons.\n\n"
        )
        txt.insert(tk.END, desc_ssim)
        txt.insert(tk.END, "Scoring Guide (Higher is Better | 0-100)\n", "h2")
        txt.insert(tk.END, "Results from average observer at 1:1 from a normal viewing distance.\n\n")
        txt.insert(tk.END, " 50  : Medium. Slightly annoying artifacts. (cjxl -d 5.0 / q45)\n", "red")
        txt.insert(tk.END, " 70  : High. Barely noticeable in a side-by-side comparison. Without reference to the original image, an average observer does not notice. (cjxl -d 2.5 / q73)\n")
        txt.insert(tk.END, " 80  : Very High. Not noticeable in a side-by-side comparison. (cjxl -d 1.5 / q85)\n")
        txt.insert(tk.END, " 85  : Excellent. Not noticeable in the condition of in-place comparison. (cjxl -d 1.0 / q90)\n")
        txt.insert(tk.END, " 90  : Vis. Lossless. Not noticeable in a flicker test. (cjxl -d 0.5 / q95)\n", "green")
        txt.insert(tk.END, " 100 : Math. Lossless.\n\n")
        txt.insert(tk.END, "-"*60 + "\n\n")

        # 2. BUTTERAUGLI
        txt.insert(tk.END, "BUTTERAUGLI\n\n", "h1")
        desc_butter = (
            "Butteraugli is a psychovisual image quality metric that estimates the perceived difference "
            "between two images. Unlike simple metrics like PSNR or MSE, butteraugli models human vision "
            "to produce scores that correlate well with subjective quality assessments. "
            "It models aspects of human vision—color sensitivity, spatial masking, and contrast perception—to highlight differences "
            "that viewers actually see. The core tool outputs a single “distance” score along with "
            "per-pixel or per-region maps that show where artifacts are most objectionable.\n\n"
        )
        txt.insert(tk.END, desc_butter)
        txt.insert(tk.END, f"Scoring Guide (Lower is Better | Target: {INTENSITY} nits)\n", "h2")
        txt.insert(tk.END, " Score < 1.0  : Identical to most viewers\n", "green")
        txt.insert(tk.END, " 1.0 - 2.0    : Subtle differences may be noticeable\n")
        txt.insert(tk.END, " Score > 2.0  : Visible differences between images\n\n", "red")
        txt.insert(tk.END, "Look at the FIRST number (peak), the 3-norm is the average. For example if the peak is 1.5 "
                           "but the 3-Norm is 0.4, the image may be visually perfect almost everywhere, with isolated compression artifacts. "
                           "Heatmap will help to check that.\n\n")
        txt.insert(tk.END, "[ HEATMAP ] ", "magenta")
        txt.insert(tk.END, "Generally speaking until you see green spots you are in vis. lossless territory.\n\n", "magenta")
        txt.insert(tk.END, "-"*60 + "\n\n")
        
        # 3. OVERALL COMPARISON
        txt.insert(tk.END, "OVERALL\n\n", "h1")
        txt.insert(tk.END, "SSIMULACRA 2\n", "h3")
        txt.insert(tk.END, "Uses a \"Structural Similarity\" approach. It cares about whether the structure of the image "
                           "(edges, textures) remains intact. It is tuned specifically to reward images that look like "
                           "the original, even if the pixel values are slightly different. It is currently considered the "
                           "gold standard for a visual quality metric.\n")
        txt.insert(tk.END, "BUTTERAUGLI\n", "h3")
        txt.insert(tk.END, "Is a \"Psychovisual Error\" metric. It calculates a \"distance\" or deviation. It cares "
                           "deeply about color artifacts and density. It is extremely sensitive to changes that might "
                           "be technically visible but not necessarily annoying.\n\n")
        txt.insert(tk.END, "The Butteraugli metric should be better at finding technical imperfections "
                           "while SSIMULACRA 2 scores correlate best with human eyes.", "bold")
        txt.config(state="disabled")

    # ==========================================
    # TAB 1: SINGLE IMAGE
    # ==========================================
    def setup_single_tab(self):
        frame = ttk.Frame(self.tab_single, padding=10)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="1. Original Image:").grid(row=0, column=0, sticky="w")
        self.ent_orig_s = ttk.Entry(frame, width=70)
        self.ent_orig_s.grid(row=0, column=1, padx=5, pady=5)
        if DND_SUPPORT:
            self.ent_orig_s.drop_target_register(DND_FILES)
            self.ent_orig_s.dnd_bind('<<Drop>>', lambda e: self.drop_handler(e, self.ent_orig_s))
        ttk.Button(frame, text="Browse", command=lambda: self.browse_file(self.ent_orig_s)).grid(row=0, column=2)

        ttk.Label(frame, text="2. Encoded Image:").grid(row=1, column=0, sticky="w")
        self.ent_dist_s = ttk.Entry(frame, width=70)
        self.ent_dist_s.grid(row=1, column=1, padx=5, pady=5)
        if DND_SUPPORT:
            self.ent_dist_s.drop_target_register(DND_FILES)
            self.ent_dist_s.dnd_bind('<<Drop>>', lambda e: self.drop_handler(e, self.ent_dist_s))
        ttk.Button(frame, text="Browse", command=lambda: self.browse_file(self.ent_dist_s)).grid(row=1, column=2)

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=1, pady=10, sticky="ew")
        ttk.Button(btn_frame, text="Info 🛈", width=8, command=self.open_info_window).pack(side="left", padx=(0, 5))
        ttk.Button(btn_frame, text="RUN ANALYSIS", command=self.start_single_thread).pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        # --- NEW BUTTONS ---
        ttk.Button(btn_frame, text="OPTIMIZER (RD)", command=self.open_optimizer).pack(side="left", padx=(5, 0))
        ttk.Button(btn_frame, text="DIFF. MAPS", command=self.open_visual_lab).pack(side="left", padx=(5, 0))
        # -------------------

        self.btn_heatmap = ttk.Button(btn_frame, text="HEATMAP", command=self.open_heatmap, state="disabled")
        self.btn_heatmap.pack(side="right", fill="x", padx=(5, 0))

        self.log_single = scrolledtext.ScrolledText(frame, height=30, bg="#1e1e1e", fg="#cccccc", font=("Consolas", 10))
        self.log_single.grid(row=3, column=0, columnspan=3, sticky="nsew", pady=10)
        
        self.log_single.tag_config("cyan", foreground="cyan")
        self.log_single.tag_config("green", foreground="#00FF00")
        self.log_single.tag_config("yellow", foreground="yellow")
        self.log_single.tag_config("red", foreground="#FF4444")
        self.log_single.tag_config("darkgray", foreground="#666666") 
        self.log_single.tag_config("magenta", foreground="magenta")

        frame.rowconfigure(3, weight=1)
        frame.columnconfigure(1, weight=1)

    def open_optimizer(self):
        OptimizerWindow(self, SSIM_EXE)

    def open_visual_lab(self):
        orig = self.ent_orig_s.get().strip().strip('"')
        dist = self.ent_dist_s.get().strip().strip('"')
        if not orig or not dist or not os.path.exists(orig) or not os.path.exists(dist):
            messagebox.showerror("Error", "Select files first.")
            return
        VisualLabWindow(self, orig, dist)

    def start_single_thread(self):
        self.btn_heatmap.config(state="disabled")
        t = threading.Thread(target=self.run_single_analysis)
        t.daemon = True
        t.start()

    def run_single_analysis(self):
        orig = self.ent_orig_s.get().strip().strip('"')
        dist = self.ent_dist_s.get().strip().strip('"')
        self.log_single.delete(1.0, tk.END)
        if not orig or not dist:
            self.log_single.insert(tk.END, "Error: Please select both images.\n", "red")
            return
        self.log(self.log_single, "=======================================================\n", "cyan")
        self.log(self.log_single, "                CALCULATING SCORES...\n")
        self.log(self.log_single, "=======================================================\n\n")

        self.log(self.log_single, "[ SSIMULACRA 2 ] (0-100)\n\n", "cyan")
        try:
            res_ssim = subprocess.run([SSIM_EXE, orig, dist], capture_output=True, text=True)
            output_ssim = res_ssim.stdout + res_ssim.stderr
            ssim_val = self.get_num(output_ssim)
            self.log(self.log_single, "RESULT: ")
            try:
                val_f = float(ssim_val)
                color = "green" if val_f >= 90 else "yellow" if val_f >= 70 else "red"
                self.log(self.log_single, f"{ssim_val}", color)
            except: self.log(self.log_single, f"{ssim_val}", "red")
            self.log(self.log_single, "\n\n\n")

            self.log(self.log_single, f"[ BUTTERAUGLI ] (Target: {INTENSITY} nits)\n\n", "cyan")
            heatmap_path = dist + "_heatmap.ppm"
            cmd_butter = [BUTTER_EXE, orig, dist, "--intensity_target", INTENSITY, "--distmap", heatmap_path]
            res_butter = subprocess.run(cmd_butter, capture_output=True, text=True)
            output_butter = res_butter.stdout + res_butter.stderr
            lines = output_butter.splitlines()
            if not lines: self.log(self.log_single, "Error: No output from Butteraugli.\n", "red")
            else:
                max_raw = lines[0]
                butter_max = self.get_num(max_raw)
                butter_norm = "N/A"
                for line in lines:
                    if "3-norm" in line:
                        match = re.search(r"3-norm:\s*(\d+(\.\d+)?)", line)
                        if match: butter_norm = match.group(1)
                self.log(self.log_single, "RESULT:\n")
                self.log(self.log_single, "Peak (Distance): ")
                try:
                    b_val_f = float(butter_max)
                    color = "green" if b_val_f < 1.0 else "yellow" if b_val_f < 2.0 else "red"
                    self.log(self.log_single, f"{butter_max}", color)
                except: self.log(self.log_single, f"{butter_max}", "red")
                self.log(self.log_single, f"   3-Norm: {butter_norm}", "darkgray")
                self.log(self.log_single, "\n\n\n")

            if os.path.exists(heatmap_path):
                self.current_heatmap = heatmap_path
                self.btn_heatmap.config(state="normal")
            self.log(self.log_single, "=======================================================\n", "cyan")
            self.log(self.log_single, "\n")
            self.log(self.log_single, "[ BUTTERAUGLI HEATMAP ] ", "magenta")
            self.log(self.log_single, f"Saved to: {heatmap_path}\n\n", "darkgray")
        except Exception as e: self.log(self.log_single, f"\nCRITICAL ERROR: {str(e)}", "red")

    def open_heatmap(self):
        if self.current_heatmap and os.path.exists(self.current_heatmap):
            try: os.startfile(self.current_heatmap)
            except: subprocess.call(['open' if os.name == 'posix' else 'xdg-open', self.current_heatmap])

    # ==========================================
    # TAB 2: BATCH FOLDER
    # ==========================================
    def setup_batch_tab(self):
        frame = ttk.Frame(self.tab_batch, padding=10)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Original Folder:").grid(row=0, column=0, sticky="w")
        self.ent_orig_b = ttk.Entry(frame, width=70)
        self.ent_orig_b.grid(row=0, column=1, padx=5, pady=5)
        if DND_SUPPORT:
            self.ent_orig_b.drop_target_register(DND_FILES)
            self.ent_orig_b.dnd_bind('<<Drop>>', lambda e: self.drop_handler(e, self.ent_orig_b))
        ttk.Button(frame, text="Browse", command=lambda: self.browse_folder(self.ent_orig_b)).grid(row=0, column=2)

        ttk.Label(frame, text="Encoded Folder:").grid(row=1, column=0, sticky="w")
        self.ent_dist_b = ttk.Entry(frame, width=70)
        self.ent_dist_b.grid(row=1, column=1, padx=5, pady=5)
        if DND_SUPPORT:
            self.ent_dist_b.drop_target_register(DND_FILES)
            self.ent_dist_b.dnd_bind('<<Drop>>', lambda e: self.drop_handler(e, self.ent_dist_b))
        ttk.Button(frame, text="Browse", command=lambda: self.browse_folder(self.ent_dist_b)).grid(row=1, column=2)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(frame, variable=self.progress_var, maximum=100, style="Contrast.Horizontal.TProgressbar")
        self.progress_bar.grid(row=2, column=0, columnspan=3, sticky="ew", pady=15)
        self.lbl_status = ttk.Label(frame, text="Ready")
        self.lbl_status.grid(row=3, column=0, columnspan=3)

        btn_row = ttk.Frame(frame)
        btn_row.grid(row=4, column=1, pady=5, sticky="ew")

        ttk.Button(btn_row, text="Info 🛈", width=8, command=self.open_info_window).pack(side="left", padx=(0, 5))
        self.btn_batch_run = ttk.Button(btn_row, text="RUN BATCH ANALYSIS", command=self.start_batch_thread)
        self.btn_batch_run.pack(side="left", fill="x", expand=True)
        
        self.btn_csv = ttk.Button(btn_row, text="CSV", width=8, command=self.save_batch_csv, state="disabled")
        self.btn_csv.pack(side="left", padx=(5, 0))
        self.btn_plot = ttk.Button(btn_row, text="PLOT", width=8, command=self.plot_batch_results, state="disabled")
        self.btn_plot.pack(side="left", padx=(5, 0))

        self.log_batch = scrolledtext.ScrolledText(frame, height=20, bg="#1e1e1e", fg="#cccccc", font=("Consolas", 10))
        self.log_batch.grid(row=5, column=0, columnspan=3, sticky="nsew", pady=10)
        
        self.log_batch.tag_config("cyan", foreground="cyan")
        self.log_batch.tag_config("green", foreground="#00FF00")
        self.log_batch.tag_config("yellow", foreground="yellow")
        self.log_batch.tag_config("red", foreground="red")
        self.log_batch.tag_config("gray", foreground="#888888")
        self.log_batch.tag_config("darkgray", foreground="#666666")

        frame.rowconfigure(5, weight=1)
        frame.columnconfigure(1, weight=1)

    def start_batch_thread(self):
        self.btn_batch_run.config(state="disabled")
        self.btn_csv.config(state="disabled")
        self.btn_plot.config(state="disabled")
        t = threading.Thread(target=self.run_batch_analysis)
        t.daemon = True
        t.start()

    def process_image_pair(self, data):
        orig_path, dist_folder, base_name = data
        target_path = os.path.join(dist_folder, base_name + ".jxl")
        if not os.path.exists(target_path):
            target_path = os.path.join(dist_folder, base_name + ".png")
            if not os.path.exists(target_path): return None

        try:
            res_s = subprocess.run([SSIM_EXE, orig_path, target_path], capture_output=True, text=True)
            s_out = res_s.stdout + res_s.stderr
            s_val = float(self.get_num(s_out)) if self.get_num(s_out) != "ERR" else -1.0
        except: s_val = -1.0

        try:
            res_b = subprocess.run([BUTTER_EXE, orig_path, target_path], capture_output=True, text=True)
            b_out = res_b.stdout + res_b.stderr
            norm3 = -1.0
            m_norm = re.search(r"3-norm:\s*(\d+(\.\d+)?)", b_out)
            if m_norm: norm3 = float(m_norm.group(1))
            clean_b_out = b_out.split("3-norm")[0] if "3-norm" in b_out else b_out
            m_max = re.search(r"(\d+(\.\d+)?)", clean_b_out)
            b_val = float(m_max.group(1)) if m_max else -1.0
        except: b_val, norm3 = -1.0, -1.0

        return {"Name": base_name, "SSIM": s_val, "Butter": b_val, "Butter3N": norm3}

    def run_batch_analysis(self):
        orig_dir = self.ent_orig_b.get().strip().strip('"')
        dist_dir = self.ent_dist_b.get().strip().strip('"')
        self.log_batch.delete(1.0, tk.END)
        if not os.path.isdir(orig_dir) or not os.path.isdir(dist_dir):
            self.log_batch.insert(tk.END, "Error: Invalid directories selected.\n")
            self.btn_batch_run.config(state="normal")
            return
        files = [f for f in os.listdir(orig_dir) if os.path.isfile(os.path.join(orig_dir, f))]
        img_exts = ['.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.jxl']
        files = [f for f in files if os.path.splitext(f)[1].lower() in img_exts]
        total = len(files)
        if total == 0:
            self.log_batch.insert(tk.END, "No image files found in Original folder.\n")
            self.btn_batch_run.config(state="normal")
            return
        self.log(self.log_batch, "==========================================\n", "cyan")
        self.log(self.log_batch, "   TURBO METRICS (Sorted & Wide)\n")
        self.log(self.log_batch, "==========================================\n")
        self.log(self.log_batch, f"Found {total} images. Starting...\n", "yellow")
        
        tasks = [(os.path.join(orig_dir, f), dist_dir, os.path.splitext(f)[0]) for f in files]
        self.last_results = []
        completed = 0
        with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            futures = [executor.submit(self.process_image_pair, task) for task in tasks]
            for future in futures:
                res = future.result()
                if res: self.last_results.append(res)
                completed += 1
                perc = (completed / total) * 100
                self.progress_var.set(perc)
                self.lbl_status.config(text=f"Analyzing... {completed}/{total}")
                self.update_idletasks()

        self.lbl_status.config(text="Analysis Complete.")
        self.last_results.sort(key=lambda x: x["Name"])

        if self.last_results:
            self.log(self.log_batch, "==========================================\n", "yellow")
            self.log(self.log_batch, "           ANALYSIS COMPLETE              \n")
            self.log(self.log_batch, "==========================================\n\n")
            self.show_stats("SSIMULACRA 2 (Higher is Better)", [r["SSIM"] for r in self.last_results], False)
            self.show_stats("BUTTERAUGLI (Lower is Better)", [r["Butter"] for r in self.last_results], True, [r["Butter3N"] for r in self.last_results])
            self.btn_csv.config(state="normal")
            if MPL_SUPPORT: self.btn_plot.config(state="normal")
        self.btn_batch_run.config(state="normal")

    def save_batch_csv(self):
        if not self.last_results: return
        dist_dir = self.ent_dist_b.get().strip().strip('"')
        names = [r["Name"] for r in self.last_results]
        try:
            p1 = os.path.join(dist_dir, "results_SSIM_wide.csv")
            with open(p1, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f); writer.writerow(["Metric"] + names); writer.writerow(["SSIM"] + [str(r["SSIM"]) for r in self.last_results])
            p2 = os.path.join(dist_dir, "results_BUTTER_wide.csv")
            with open(p2, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f); writer.writerow(["Metric"] + names); writer.writerow(["Butter_Max"] + [str(r["Butter"]) for r in self.last_results]); writer.writerow(["Butter_3N"] + [str(r["Butter3N"]) for r in self.last_results])
            messagebox.showinfo("Success", f"CSVs saved in:\n{dist_dir}")
        except Exception as e: messagebox.showerror("Error", f"Could not save CSV: {str(e)}")

    def plot_batch_results(self):
        if not MPL_SUPPORT:
            messagebox.showwarning("Missing Library", "Matplotlib not found.")
            return
        
        names = [r["Name"] for r in self.last_results]
        ssim = [r["SSIM"] for r in self.last_results]
        b_max = [r["Butter"] for r in self.last_results]
        b_3n = [r["Butter3N"] for r in self.last_results]

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 4.5), gridspec_kw={'height_ratios': [1, 2]})
        fig.subplots_adjust(hspace=0.3, right=0.98, left=0.1, bottom=0.1, top=0.90)
        
        fig.canvas.manager.set_window_title("Batch Analysis Results")

        # Plot SSIM (Top) - Spectral colormap, Blue is high (100), Red is low (50)
        ssim_data = np.array([ssim])
        im1 = ax1.imshow(ssim_data, cmap='Spectral', aspect='auto', vmin=50, vmax=100)
        ax1.set_yticks([0]); ax1.set_yticklabels(["SSIM 2"]); ax1.set_xticks([])
        fig.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04).set_label('Quality (0-100)')

        # Plot Butter (Bottom) - Spectral_r (reversed), Blue is low (0), Red is high (3.0)
        butter_data = np.array([b_max, b_3n])
        im2 = ax2.imshow(butter_data, cmap='Spectral_r', aspect='auto', vmin=0, vmax=3.0)
        ax2.set_yticks([0, 1]); ax2.set_yticklabels(["Butter_Max", "Butter_3N"]); ax2.set_xticks([])
        fig.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04).set_label('Distance')

        ax1.format_coord = lambda x, y: ""
        ax2.format_coord = lambda x, y: ""

        def hover(event):
            if event.inaxes in [ax1, ax2]:
                try:
                    col = int(round(event.xdata))
                    if 0 <= col < len(names):
                        n = names[col]
                        s = ssim[col]
                        bm = b_max[col]
                        b3 = b_3n[col]
                        msg = f"File: {n}  |  SSIM: {s:.2f}  |  Butter Peak: {bm:.2f}  |  Butter 3N: {b3:.2f}"
                        fig.canvas.toolbar.set_message(msg)
                    else:
                        fig.canvas.toolbar.set_message("")
                except:
                    fig.canvas.toolbar.set_message("")
            else:
                fig.canvas.toolbar.set_message("")

        fig.canvas.mpl_connect("motion_notify_event", hover)
        plt.show()

    def show_stats(self, title, data_list, is_butter, sec_list=None):
        valid = [x for x in data_list if x >= 0]
        if not valid: return
        valid.sort()
        avg, median, d_min, d_max = statistics.mean(valid), statistics.median(valid), valid[0], valid[-1]
        idx = int(len(valid) * (0.95 if is_butter else 0.05))
        p_val = valid[min(idx, len(valid)-1)]
        p_label = "95th % (Worst)" if is_butter else "5th %  (Worst)"
        color = "cyan" if is_butter else "green"

        self.log(self.log_batch, "-"*32 + "\n", "gray")
        self.log(self.log_batch, f" {title}\n", color)
        self.log(self.log_batch, "-"*32 + "\n", "gray")
        self.log(self.log_batch, f" Average:  {avg:.4f}")
        if sec_list:
            v2 = [x for x in sec_list if x >= 0]
            if v2: self.log(self.log_batch, f" (3-Norm Avg: {statistics.mean(v2):.4f})", "darkgray")
        self.log(self.log_batch, f"\n Median:   {median:.4f}\n Min:      {d_min:.4f}\n Max:      {d_max:.4f}\n {p_label}: {p_val:.4f}\n\n")

    def browse_file(self, entry):
        f = filedialog.askopenfilename()
        if f: entry.delete(0, tk.END); entry.insert(0, f)
    def browse_folder(self, entry):
        d = filedialog.askdirectory()
        if d: entry.delete(0, tk.END); entry.insert(0, d)
    def log(self, widget, text, tag=None):
        widget.insert(tk.END, text, tag); widget.see(tk.END)
    def get_num(self, text):
        m = re.search(r"(\d+(\.\d+)?)", text)
        return m.group(0) if m else "ERR"

if __name__ == "__main__":
    app = MetricToolGUI(); app.mainloop()