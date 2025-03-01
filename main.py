import tkinter as tk
from tkinter import filedialog, Scale, Frame, Button, Label
from PIL import Image, ImageTk, ImageEnhance
import numpy as np
import os
import threading
import time

class PixelPhotoEditor:
    def __init__(self, root):
        self.root = root
        self.root.title("Pixelated Photo Editor")
        self.root.geometry("1000x700")
        
        self.original_image = None
        self.working_image = None  # Downscaled version for preview
        self.processed_image = None
        self.filename = None
        self.processing = False
        self.max_preview_dimension = 1200  # Maximum dimension for preview
        self.max_output_dimension = 2000   # Maximum dimension for saved images
        
        # Main frames
        self.left_frame = Frame(root, width=200, bg="#2c3e50")
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        self.right_frame = Frame(root, bg="#34495e")
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = Label(self.right_frame, textvariable=self.status_var, 
                               bg="#34495e", fg="white", anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
        
        # Image display area
        self.canvas = tk.Canvas(self.right_frame, bg="#34495e", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Control elements
        Label(self.left_frame, text="PIXEL EDITOR", font=("Arial", 16, "bold"), 
              bg="#2c3e50", fg="white").pack(pady=(20, 30))
        
        Button(self.left_frame, text="Open Image", command=self.open_image,
               bg="#3498db", fg="white", font=("Arial", 12), width=15).pack(pady=10)
        
        Label(self.left_frame, text="Pixel Size", bg="#2c3e50", fg="white", 
              font=("Arial", 12)).pack(pady=(20, 5))
        self.pixel_size_slider = Scale(self.left_frame, from_=2, to=40, orient=tk.HORIZONTAL,
                                       length=180, bg="#2c3e50", fg="white", 
                                       highlightthickness=0, command=self.queue_update)
        self.pixel_size_slider.set(10)
        self.pixel_size_slider.pack()
        
        Label(self.left_frame, text="Color Shift", bg="#2c3e50", fg="white", 
              font=("Arial", 12)).pack(pady=(20, 5))
        self.color_shift_slider = Scale(self.left_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                                        length=180, bg="#2c3e50", fg="white", 
                                        highlightthickness=0, command=self.queue_update)
        self.color_shift_slider.set(50)
        self.color_shift_slider.pack()
        
        # New Exposure Slider
        Label(self.left_frame, text="Exposure", bg="#2c3e50", fg="white", 
              font=("Arial", 12)).pack(pady=(20, 5))
        self.exposure_slider = Scale(self.left_frame, from_=0.5, to=1.5, resolution=0.1, 
                                     orient=tk.HORIZONTAL, length=180, bg="#2c3e50", fg="white", 
                                     highlightthickness=0, command=self.queue_update)
        self.exposure_slider.set(1.0)
        self.exposure_slider.pack()
        
        Label(self.left_frame, text="Contrast", bg="#2c3e50", fg="white", 
              font=("Arial", 12)).pack(pady=(20, 5))
        self.contrast_slider = Scale(self.left_frame, from_=0.5, to=2.0, resolution=0.1, 
                                     orient=tk.HORIZONTAL, length=180, bg="#2c3e50", fg="white", 
                                     highlightthickness=0, command=self.queue_update)
        self.contrast_slider.set(1.2)
        self.contrast_slider.pack()
        
        Label(self.left_frame, text="Saturation", bg="#2c3e50", fg="white", 
              font=("Arial", 12)).pack(pady=(20, 5))
        self.saturation_slider = Scale(self.left_frame, from_=0.0, to=2.0, resolution=0.1, 
                                       orient=tk.HORIZONTAL, length=180, bg="#2c3e50", fg="white", 
                                       highlightthickness=0, command=self.queue_update)
        self.saturation_slider.set(1.4)
        self.saturation_slider.pack()
        
        # Color palette selection
        Label(self.left_frame, text="Color Palette", bg="#2c3e50", fg="white", 
              font=("Arial", 12)).pack(pady=(20, 5))
        
        self.palette_var = tk.StringVar()
        self.palette_var.set("retro")
        
        # Expanded palette selection
        palettes = [
            ("Retro", "retro"),
            ("Cyberpunk", "cyberpunk"),
            ("Vaporwave", "vaporwave"),
            ("Mono", "mono"),
            ("Neon", "neon"),
            ("Pastel", "pastel"),
            ("Autumn", "autumn"),
            ("Sunset", "sunset")
        ]
        
        # Create a frame for the palette options to allow scrolling if needed
        palette_frame = Frame(self.left_frame, bg="#2c3e50")
        palette_frame.pack(fill=tk.X, padx=10, pady=5)
        
        for text, value in palettes:
            tk.Radiobutton(palette_frame, text=text, variable=self.palette_var, value=value,
                          bg="#2c3e50", fg="white", selectcolor="#2c3e50", 
                          activebackground="#2c3e50", command=self.queue_update).pack(anchor=tk.W, padx=10)
        
        Button(self.left_frame, text="Save Image", command=self.save_image,
               bg="#2ecc71", fg="white", font=("Arial", 12), width=15).pack(pady=(40, 10))
        
        # Display initial message
        self.display_welcome_message()
        
        # Configure the update checking
        self.update_queued = False
        self.last_update_time = 0
        self.update_delay = 300  # ms
        self.root.after(100, self.check_update_queue)

    def display_welcome_message(self):
        self.canvas.delete("all")
        self.canvas.create_text(
            self.canvas.winfo_width() // 2, 
            self.canvas.winfo_height() // 2,
            text="Open an image to begin editing",
            font=("Arial", 16),
            fill="white"
        )

    def open_image(self):
        if self.processing:
            return
            
        self.filename = filedialog.askopenfilename(
            title="Select an image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.gif")]
        )
        
        if self.filename:
            self.status_var.set("Loading image...")
            self.root.update()
            threading.Thread(target=self._load_image, daemon=True).start()
    
    def _load_image(self):
        try:
            self.processing = True
            self.original_image = Image.open(self.filename)
            self.working_image = self.downscale_for_preview(self.original_image)
            self.queue_update()
        except Exception as e:
            self.status_var.set(f"Error loading image: {str(e)}")
        finally:
            self.processing = False
    
    def downscale_for_preview(self, img):
        width, height = img.size
        if width <= self.max_preview_dimension and height <= self.max_preview_dimension:
            return img.copy()
        scale = min(self.max_preview_dimension / width, self.max_preview_dimension / height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        return img.resize((new_width, new_height), Image.BILINEAR)

    def adjust_exposure(self, img, factor):
        enhancer = ImageEnhance.Brightness(img)
        return enhancer.enhance(factor)

    def adjust_contrast(self, img, factor):
        enhancer = ImageEnhance.Contrast(img)
        return enhancer.enhance(factor)

    def adjust_saturation(self, img, factor):
        enhancer = ImageEnhance.Color(img)
        return enhancer.enhance(factor)

    def apply_color_palette(self, img, palette_name, shift_amount):
        palettes = {
            "retro": [
                [60, 35, 80],    [100, 60, 120], [200, 80, 100],
                [255, 170, 80],  [255, 240, 120]
            ],
            "cyberpunk": [
                [10, 10, 40],    [30, 60, 120],  [0, 220, 220],
                [255, 50, 120], [255, 240, 0]
            ],
            "vaporwave": [
                [100, 20, 100], [180, 50, 190], [0, 205, 205],
                [255, 120, 180],[180, 230, 255]
            ],
            "mono": [
                [20, 20, 20],   [80, 80, 80],   [150, 150, 150],
                [220, 220, 220],[250, 250, 250]
            ],
            "neon": [
                [10, 10, 30],    [30, 0, 80],    [255, 0, 180],
                [0, 255, 160],   [0, 240, 255]
            ],
            "pastel": [
                [240, 210, 210], [210, 240, 220], [210, 220, 240],
                [240, 230, 210], [225, 210, 240]
            ],
            "autumn": [
                [40, 20, 10],    [120, 60, 20],  [210, 110, 40],
                [230, 180, 80],  [180, 120, 100]
            ],
            "sunset": [
                [20, 20, 50],    [80, 30, 90],   [180, 60, 80],
                [240, 120, 50],  [255, 210, 100]
            ]
        }
        
        palette = np.array(palettes[palette_name])
        if shift_amount > 0:
            shift = int((shift_amount / 100) * 3)
            palette = np.roll(palette, shift, axis=0)
        
        img_array = np.array(img)
        h, w, c = img_array.shape
        pixels = img_array.reshape(-1, c)
        
        distances = np.sum((pixels[:, np.newaxis, :] - palette[np.newaxis, :, :]) ** 2, axis=2)
        closest_indices = np.argmin(distances, axis=1)
        
        result = palette[closest_indices].reshape(h, w, c).astype(np.uint8)
        return Image.fromarray(result)

    def pixelate_image(self, img, pixel_size):
        width, height = img.size
        small_width = max(1, width // pixel_size)
        small_height = max(1, height // pixel_size)
        return img.resize((small_width, small_height), Image.NEAREST)\
                 .resize((width, height), Image.NEAREST)

    def process_image(self, preview=True, source_img=None):
        if self.original_image is None:
            return None
        try:
            self.status_var.set("Processing image...")
            self.root.update()
            pixel_size = self.pixel_size_slider.get()
            color_shift = self.color_shift_slider.get()
            exposure_factor = self.exposure_slider.get()
            contrast_factor = self.contrast_slider.get()
            saturation_factor = self.saturation_slider.get()
            palette = self.palette_var.get()
            
            if source_img is not None:
                source = source_img
            else:
                source = self.working_image if preview else self.original_image
            
            img = source.copy()
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img = self.adjust_exposure(img, exposure_factor)
            img = self.adjust_contrast(img, contrast_factor)
            img = self.adjust_saturation(img, saturation_factor)
            img = self.pixelate_image(img, pixel_size)
            img = self.apply_color_palette(img, palette, color_shift)
            self.status_var.set("Ready")
            return img
        except Exception as e:
            self.status_var.set(f"Error processing image: {str(e)}")
            return None

    def queue_update(self, *args):
        self.update_queued = True
        self.last_update_time = time.time() * 1000

    def check_update_queue(self):
        current_time = time.time() * 1000
        if (self.update_queued and 
            current_time - self.last_update_time > self.update_delay and 
            not self.processing):
            self.update_queued = False
            self.processing = True
            threading.Thread(target=self._process_and_update, daemon=True).start()
        self.root.after(100, self.check_update_queue)
    
    def _process_and_update(self):
        try:
            self.processed_image = self.process_image(preview=True)
            if self.processed_image:
                self.update_display()
        finally:
            self.processing = False

    def update_display(self):
        if self.processed_image:
            self.canvas.delete("all")
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            if canvas_width <= 1 or canvas_height <= 1:
                canvas_width = self.root.winfo_width() - 200
                canvas_height = self.root.winfo_height()
            img_width, img_height = self.processed_image.size
            scale = min(canvas_width / img_width, canvas_height / img_height)
            if scale < 1:
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
                display_img = self.processed_image.resize((new_width, new_height), Image.NEAREST)
            else:
                display_img = self.processed_image
            self.tk_image = ImageTk.PhotoImage(display_img)
            x = max(0, (canvas_width - self.tk_image.width()) // 2)
            y = max(0, (canvas_height - self.tk_image.height()) // 2)
            self.image_on_canvas = self.canvas.create_image(x, y, anchor=tk.NW, image=self.tk_image)
    
    def downscale_for_output(self, img):
        width, height = img.size
        if width <= self.max_output_dimension and height <= self.max_output_dimension:
            return img.copy()
        scale = min(self.max_output_dimension / width, self.max_output_dimension / height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        return img.resize((new_width, new_height), Image.BILINEAR)

    def save_image(self):
        if self.original_image is None or self.processing:
            return
        original_ext = os.path.splitext(self.filename)[1] if self.filename else ".png"
        save_path = filedialog.asksaveasfilename(
            defaultextension=original_ext,
            initialfile=f"{os.path.basename(self.filename).replace(' ', '_')}_pixelated",
            filetypes=[
                ("PNG", "*.png"),
                ("JPEG", "*.jpg *.jpeg"),
                ("BMP", "*.bmp"),
                ("All Files", "*.*")
            ]
        )
        if save_path:
            self.status_var.set("Processing full resolution image...")
            self.root.update()
            threading.Thread(target=self._process_and_save, args=(save_path,), daemon=True).start()
    
    def _process_and_save(self, save_path):
        try:
            self.processing = True
            output_image = self.downscale_for_output(self.original_image)
            full_res_image = self.process_image(preview=False, source_img=output_image)
            if full_res_image:
                full_res_image.save(save_path)
                self.status_var.set(f"Saved to {os.path.basename(save_path)}")
            else:
                self.status_var.set("Error processing image for saving")
        except Exception as e:
            self.status_var.set(f"Error saving image: {str(e)}")
        finally:
            self.processing = False


if __name__ == "__main__":
    root = tk.Tk()
    app = PixelPhotoEditor(root)
    root.mainloop()