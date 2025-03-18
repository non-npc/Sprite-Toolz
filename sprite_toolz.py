#!/usr/bin/env python3
import sys
import os
import numpy as np
from PIL import Image
import imageio
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QScrollArea, 
                            QVBoxLayout, QHBoxLayout, QWidget, QPushButton, 
                            QFileDialog, QSpinBox, QCheckBox, QColorDialog, 
                            QGridLayout, QGroupBox, QSlider, QFrame, QSizePolicy,
                            QMessageBox, QTabWidget, QRadioButton)
from PyQt6.QtGui import QPixmap, QPainter, QPen, QColor, QImage, QCursor
from PyQt6.QtCore import Qt, QRect, QSize, QPoint


class SpriteCanvas(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.spritesheet = None
        self.sprite_image = None
        self.original_image = None  # Store the original image without padding
        self.cell_width = 32
        self.cell_height = 32
        self.show_grid = True
        self.grid_color = QColor(255, 0, 0, 128)  # Semi-transparent red
        self.padding = 0
        self.padding_preview = 0  # New variable for padding preview
        self.setMinimumSize(800, 600)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)  # Enable mouse tracking for hover effects
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center the image
        
        # Zoom variables
        self.zoom_factor = 1.0  # Default zoom level (1x)
        self.zoom_levels = [1.0, 2.0, 4.0, 6.0]  # Available zoom levels
        self.current_zoom_index = 0  # Start at 1x zoom
        
        # Create a checkered background for transparent sprites
        self.setStyleSheet("background-color: white;")
        
        # Selection variables
        self.selected_cells = []
        self.selection_start = None
        self.selection_end = None
        self.is_selecting = False
        self.selected_row = -1
        self.selected_column = -1
        
        # Add custom frame selection variables
        self.custom_frame_selection = []  # List to store frames in selection order
        self.is_custom_selecting = False  # Flag for custom selection mode
        
    def load_spritesheet(self, filename):
        self.sprite_image = Image.open(filename)
        self.original_image = self.sprite_image.copy()  # Store original image
        self.spritesheet = np.array(self.sprite_image)
        self.update_pixmap()
        
    def update_pixmap(self):
        if self.sprite_image is None:
            return
            
        # Convert PIL Image to QPixmap with proper transparency
        if self.sprite_image.mode == 'RGBA':
            # For RGBA images (with transparency)
            data = self.sprite_image.tobytes("raw", "RGBA")
            qim = QImage(data, self.sprite_image.size[0], self.sprite_image.size[1], 
                       self.sprite_image.size[0] * 4, QImage.Format.Format_RGBA8888)
        elif self.sprite_image.mode == 'RGB':
            # For RGB images (no transparency)
            data = self.sprite_image.tobytes("raw", "RGB")
            qim = QImage(data, self.sprite_image.size[0], self.sprite_image.size[1], 
                       self.sprite_image.size[0] * 3, QImage.Format.Format_RGB888)
        else:
            # Convert other modes to RGBA for consistent handling
            converted_img = self.sprite_image.convert('RGBA')
            data = converted_img.tobytes("raw", "RGBA")
            qim = QImage(data, converted_img.size[0], converted_img.size[1], 
                       converted_img.size[0] * 4, QImage.Format.Format_RGBA8888)
            
        # Create pixmap and set it to the label
        pixmap = QPixmap.fromImage(qim)
        
        # Apply zoom if needed
        if self.zoom_factor != 1.0:
            zoom_width = int(pixmap.width() * self.zoom_factor)
            zoom_height = int(pixmap.height() * self.zoom_factor)
            pixmap = pixmap.scaled(zoom_width, zoom_height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)
        
        self.setPixmap(pixmap)
        
        # Set an appropriate size for the canvas
        self.resize(pixmap.size())
        self.setMinimumSize(pixmap.size())
        
        # Ensure update
        self.update()
    
    def mousePressEvent(self, event):
        if self.sprite_image is None:
            return
            
        if event.button() == Qt.MouseButton.LeftButton:
            x, y = event.position().x(), event.position().y()
            
            # Calculate offset for centering
            x_offset = max(0, (self.width() - int(self.sprite_image.size[0] * self.zoom_factor)) // 2)
            y_offset = max(0, (self.height() - int(self.sprite_image.size[1] * self.zoom_factor)) // 2)
            
            # Adjust for offset
            x = x - x_offset
            y = y - y_offset
            
            # Check if click is outside the image area
            if (x < 0 or y < 0 or 
                x >= self.sprite_image.size[0] * self.zoom_factor or 
                y >= self.sprite_image.size[1] * self.zoom_factor):
                return
            
            # Account for zoom factor when calculating cell coordinates
            cell_x = int(x // (self.cell_width * self.zoom_factor))
            cell_y = int(y // (self.cell_height * self.zoom_factor))
            
            # Get keyboard modifiers
            modifiers = QApplication.keyboardModifiers()
            
            # Check for Ctrl+Shift combination for custom frame selection
            if (modifiers & Qt.KeyboardModifier.ControlModifier and 
                modifiers & Qt.KeyboardModifier.ShiftModifier):
                # Custom frame selection mode
                self.is_custom_selecting = True
                frame_pos = (cell_x, cell_y)
                if frame_pos not in self.custom_frame_selection:
                    self.custom_frame_selection.append(frame_pos)
                else:
                    self.custom_frame_selection.remove(frame_pos)
                self.selected_cells = self.custom_frame_selection.copy()
                self.selected_row = -1
                self.selected_column = -1
            else:
                # Regular selection mode
                self.is_custom_selecting = False
                self.custom_frame_selection.clear()
                self.selected_cells = []
                self.selection_start = (cell_x, cell_y)
                self.selection_end = (cell_x, cell_y)
                
                # Select the whole row or column if holding Shift or Ctrl
                if modifiers & Qt.KeyboardModifier.ShiftModifier:
                    self.selected_row = cell_y
                    self.selected_column = -1
                elif modifiers & Qt.KeyboardModifier.ControlModifier:
                    self.selected_column = cell_x
                    self.selected_row = -1
                else:
                    self.selected_row = -1
                    self.selected_column = -1
                
            self.is_selecting = True
            self.update_selection()
            self.update()
            
            # Update UI
            if hasattr(self.parent().parent().parent(), 'update_selection_label'):
                self.parent().parent().parent().update_selection_label()
            if hasattr(self.parent().parent().parent(), 'update_button_states'):
                self.parent().parent().parent().update_button_states()
    
    def mouseMoveEvent(self, event):
        if self.sprite_image is None or self.is_custom_selecting:
            return
            
        if self.is_selecting and event.buttons() & Qt.MouseButton.LeftButton:
            x, y = event.position().x(), event.position().y()
            
            # Calculate offset for centering
            x_offset = max(0, (self.width() - int(self.sprite_image.size[0] * self.zoom_factor)) // 2)
            y_offset = max(0, (self.height() - int(self.sprite_image.size[1] * self.zoom_factor)) // 2)
            
            # Adjust for offset
            x = x - x_offset
            y = y - y_offset
            
            # Clamp coordinates to image boundaries
            x = max(0, min(x, self.sprite_image.size[0] * self.zoom_factor - 1))
            y = max(0, min(y, self.sprite_image.size[1] * self.zoom_factor - 1))
            
            # Account for zoom factor when calculating cell coordinates
            cell_x = max(0, min(int(x // (self.cell_width * self.zoom_factor)), 
                                int(self.sprite_image.size[0] // self.cell_width) - 1))
            cell_y = max(0, min(int(y // (self.cell_height * self.zoom_factor)), 
                                int(self.sprite_image.size[1] // self.cell_height) - 1))
            
            self.selection_end = (cell_x, cell_y)
            self.update_selection()
            self.update()
            
            # Update UI
            if hasattr(self.parent().parent().parent(), 'update_selection_label'):
                self.parent().parent().parent().update_selection_label()
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.is_selecting = False
            
            # Update UI
            if hasattr(self.parent().parent().parent(), 'update_selection_label'):
                self.parent().parent().parent().update_selection_label()
            if hasattr(self.parent().parent().parent(), 'update_button_states'):
                self.parent().parent().parent().update_button_states()
    
    def update_selection(self):
        if self.is_custom_selecting:
            # For custom selection, selected_cells is already updated
            return
            
        if self.selection_start is None or self.selection_end is None:
            return
            
        if self.selected_row >= 0:
            # Select entire row
            row = self.selected_row
            max_cols = self.sprite_image.size[0] // self.cell_width
            self.selected_cells = [(col, row) for col in range(max_cols)]
        elif self.selected_column >= 0:
            # Select entire column
            col = self.selected_column
            max_rows = self.sprite_image.size[1] // self.cell_height
            self.selected_cells = [(col, row) for row in range(max_rows)]
        else:
            # Select rectangle of cells
            start_x, start_y = self.selection_start
            end_x, end_y = self.selection_end
            
            min_x, max_x = min(start_x, end_x), max(start_x, end_x)
            min_y, max_y = min(start_y, end_y), max(start_y, end_y)
            
            self.selected_cells = []
            for y in range(min_y, max_y + 1):
                for x in range(min_x, max_x + 1):
                    self.selected_cells.append((x, y))
    
    def paintEvent(self, event):
        # Draw checkered background for transparency
        painter = QPainter(self)
        
        # Create checkered pattern for transparent areas
        checker_size = 10
        light_gray = QColor(220, 220, 220)
        white = QColor(255, 255, 255)
        
        for y in range(0, self.height(), checker_size):
            for x in range(0, self.width(), checker_size):
                color = light_gray if ((x // checker_size) + (y // checker_size)) % 2 else white
                painter.fillRect(x, y, checker_size, checker_size, color)
        
        # Center the pixmap in the canvas
        if self.pixmap() and not self.pixmap().isNull():
            # Calculate center position
            x_offset = max(0, (self.width() - self.pixmap().width()) // 2)
            y_offset = max(0, (self.height() - self.pixmap().height()) // 2)
            
            # Draw the pixmap at the centered position
            painter.drawPixmap(x_offset, y_offset, self.pixmap())
        
        if self.sprite_image is None:
            painter.end()
            return
        
        # Get center offset for grid and selection drawing
        x_offset = max(0, (self.width() - int(self.sprite_image.size[0] * self.zoom_factor)) // 2)
        y_offset = max(0, (self.height() - int(self.sprite_image.size[1] * self.zoom_factor)) // 2)
        
        # Draw the grid
        if self.show_grid:
            pen = QPen(self.grid_color)
            pen.setWidth(1)
            painter.setPen(pen)
            
            # Draw vertical lines with zoom factor
            cell_width_zoomed = self.cell_width * self.zoom_factor
            sprite_width_zoomed = self.sprite_image.size[0] * self.zoom_factor
            
            # Draw all vertical lines including the right edge
            for x in range(0, int(sprite_width_zoomed) + 1, int(cell_width_zoomed)):
                painter.drawLine(
                    x + x_offset, 
                    y_offset, 
                    x + x_offset, 
                    int(self.sprite_image.size[1] * self.zoom_factor) + y_offset
                )
                
            # Draw horizontal lines with zoom factor
            cell_height_zoomed = self.cell_height * self.zoom_factor
            sprite_height_zoomed = self.sprite_image.size[1] * self.zoom_factor
            
            # Draw all horizontal lines including the bottom edge
            for y in range(0, int(sprite_height_zoomed) + 1, int(cell_height_zoomed)):
                painter.drawLine(
                    x_offset, 
                    y + y_offset, 
                    int(sprite_width_zoomed) + x_offset, 
                    y + y_offset
                )
        
        # Draw selection
        if self.selected_cells:
            highlight_color = QColor(0, 0, 255, 80)  # Semi-transparent blue
            painter.setBrush(highlight_color)
            painter.setPen(Qt.PenStyle.NoPen)
            
            for cell_x, cell_y in self.selected_cells:
                rect = QRect(
                    int(cell_x * self.cell_width * self.zoom_factor) + x_offset, 
                    int(cell_y * self.cell_height * self.zoom_factor) + y_offset,
                    int(self.cell_width * self.zoom_factor), 
                    int(self.cell_height * self.zoom_factor)
                )
                painter.drawRect(rect)
            
            # Draw bold outline around selection
            outline_color = QColor(0, 0, 255, 200)  # More opaque blue
            painter.setPen(QPen(outline_color, 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
            if self.selected_row >= 0:
                # Draw row outline
                rect = QRect(
                    x_offset, 
                    int(self.selected_row * self.cell_height * self.zoom_factor) + y_offset,
                    int(self.sprite_image.size[0] * self.zoom_factor), 
                    int(self.cell_height * self.zoom_factor)
                )
                painter.drawRect(rect)
            elif self.selected_column >= 0:
                # Draw column outline
                rect = QRect(
                    int(self.selected_column * self.cell_width * self.zoom_factor) + x_offset, 
                    y_offset,
                    int(self.cell_width * self.zoom_factor), 
                    int(self.sprite_image.size[1] * self.zoom_factor)
                )
                painter.drawRect(rect)
            else:
                # Draw rectangle outline
                start_x, start_y = self.selection_start
                end_x, end_y = self.selection_end
                
                min_x, max_x = min(start_x, end_x), max(start_x, end_x)
                min_y, max_y = min(start_y, end_y), max(start_y, end_y)
                
                rect = QRect(
                    int(min_x * self.cell_width * self.zoom_factor) + x_offset, 
                    int(min_y * self.cell_height * self.zoom_factor) + y_offset,
                    int((max_x - min_x + 1) * self.cell_width * self.zoom_factor), 
                    int((max_y - min_y + 1) * self.cell_height * self.zoom_factor)
                )
                painter.drawRect(rect)
                
        painter.end()
        
    def set_cell_size(self, width, height):
        self.cell_width = width
        self.cell_height = height
        self.update()
        
    def set_grid_visible(self, visible):
        """Set grid visibility and force update"""
        self.show_grid = visible
        self.update()  # Force a repaint
        
    def set_grid_color(self, color):
        self.grid_color = color
        self.update()
        
    def set_padding(self, padding):
        """Preview padding without applying it"""
        if self.sprite_image is None or padding == self.padding_preview:
            return
            
        self.padding_preview = padding
        
        if padding == 0:
            # Reset to original image for preview
            self.sprite_image = self.original_image.copy()
            self.spritesheet = np.array(self.sprite_image)
            self.update_pixmap()
            return
            
        # Calculate number of cells in the sheet
        cols = self.original_image.size[0] // self.cell_width
        rows = self.original_image.size[1] // self.cell_height
        
        # Create a new image with padding for preview
        padded_width = cols * (self.cell_width + 2 * padding)
        padded_height = rows * (self.cell_height + 2 * padding)
        padded_image = Image.new(
            self.original_image.mode, 
            (padded_width, padded_height), 
            (0, 0, 0, 0)  # Transparent background
        )
        
        # Copy each cell with padding
        for row in range(rows):
            for col in range(cols):
                # Source coordinates from original image
                src_x = col * self.cell_width
                src_y = row * self.cell_height
                
                # Destination coordinates (with padding)
                dst_x = col * (self.cell_width + 2 * padding) + padding
                dst_y = row * (self.cell_height + 2 * padding) + padding
                
                # Extract cell from original image and paste it in the new image
                cell = self.original_image.crop(
                    (src_x, src_y, src_x + self.cell_width, src_y + self.cell_height)
                )
                padded_image.paste(cell, (dst_x, dst_y))
        
        # Update the sprite image for preview
        self.sprite_image = padded_image
        self.spritesheet = np.array(self.sprite_image)
        self.update_pixmap()

    def apply_padding(self):
        """Actually apply the padding permanently"""
        if self.sprite_image is None or self.padding_preview == 0:
            return
            
        # Update the original image with the current padded version
        self.original_image = self.sprite_image.copy()
        
        # Update cell dimensions to include padding
        self.cell_width = self.cell_width + 2 * self.padding_preview
        self.cell_height = self.cell_height + 2 * self.padding_preview
        
        # Reset padding preview
        self.padding_preview = 0
        
        # Update display
        self.update_pixmap()
        
    def remove_row(self, row_index):
        if self.sprite_image is None or row_index < 0:
            return False
            
        # Calculate number of cells in the sheet
        cols = self.sprite_image.size[0] // self.cell_width
        rows = self.sprite_image.size[1] // self.cell_height
        
        if row_index >= rows:
            return False
            
        # Create a new image without the selected row
        new_width = self.sprite_image.size[0]
        new_height = self.sprite_image.size[1] - self.cell_height
        new_image = Image.new(
            self.sprite_image.mode, 
            (new_width, new_height), 
            (0, 0, 0, 0)  # Transparent background
        )
        
        # Copy each row except the one to be removed
        y_offset = 0
        for row in range(rows):
            if row == row_index:
                continue
                
            # Source coordinates for this row
            src_y = row * self.cell_height
            
            # Extract row and paste it in the new image
            row_img = self.sprite_image.crop(
                (0, src_y, new_width, src_y + self.cell_height)
            )
            new_image.paste(row_img, (0, y_offset))
            y_offset += self.cell_height
        
        # Update the sprite image
        self.sprite_image = new_image
        self.spritesheet = np.array(self.sprite_image)
        
        # Clear selection
        self.selected_cells = []
        self.selected_row = -1
        
        # Update display
        self.update_pixmap()
        return True
        
    def remove_column(self, col_index):
        if self.sprite_image is None or col_index < 0:
            return False
            
        # Calculate number of cells in the sheet
        cols = self.sprite_image.size[0] // self.cell_width
        rows = self.sprite_image.size[1] // self.cell_height
        
        if col_index >= cols:
            return False
            
        # Create a new image without the selected column
        new_width = self.sprite_image.size[0] - self.cell_width
        new_height = self.sprite_image.size[1]
        new_image = Image.new(
            self.sprite_image.mode, 
            (new_width, new_height), 
            (0, 0, 0, 0)  # Transparent background
        )
        
        # Copy each column except the one to be removed
        x_offset = 0
        for col in range(cols):
            if col == col_index:
                continue
                
            # Source coordinates for this column
            src_x = col * self.cell_width
            
            # Extract column and paste it in the new image
            col_img = self.sprite_image.crop(
                (src_x, 0, src_x + self.cell_width, new_height)
            )
            new_image.paste(col_img, (x_offset, 0))
            x_offset += self.cell_width
        
        # Update the sprite image
        self.sprite_image = new_image
        self.spritesheet = np.array(self.sprite_image)
        
        # Clear selection
        self.selected_cells = []
        self.selected_column = -1
        
        # Update display
        self.update_pixmap()
        return True
        
    def export_selection_as_gif(self, filename):
        if not self.selected_cells or self.sprite_image is None:
            return False
            
        # Extract selected cells as frames
        frames = []
        
        # If using custom frame selection, use the frames in selection order
        if self.is_custom_selecting:
            for col, row in self.custom_frame_selection:
                # Extract the frame
                x = col * self.cell_width
                y = row * self.cell_height
                frame = self.sprite_image.crop(
                    (x, y, x + self.cell_width, y + self.cell_height)
                )
                frames.append(frame)
        else:
            # If a row is selected, export frames horizontally
            if self.selected_row >= 0:
                row = self.selected_row
                max_cols = self.sprite_image.size[0] // self.cell_width
                
                for col in range(max_cols):
                    # Extract the frame
                    x = col * self.cell_width
                    y = row * self.cell_height
                    frame = self.sprite_image.crop(
                        (x, y, x + self.cell_width, y + self.cell_height)
                    )
                    frames.append(frame)
                
            # If a column is selected, export frames vertically
            elif self.selected_column >= 0:
                col = self.selected_column
                max_rows = self.sprite_image.size[1] // self.cell_height
                
                for row in range(max_rows):
                    # Extract the frame
                    x = col * self.cell_width
                    y = row * self.cell_height
                    frame = self.sprite_image.crop(
                        (x, y, x + self.cell_width, y + self.cell_height)
                    )
                    frames.append(frame)
                
            # If a custom selection is made, export frames in reading order
            else:
                # Sort cells by row then column for reading order
                cells = sorted(self.selected_cells, key=lambda c: (c[1], c[0]))
        
        # Save frames as GIF animation
        if frames:
            frames[0].save(
                filename,
                format='GIF',
                append_images=frames[1:],
                save_all=True,
                duration=100,  # 100ms per frame
                loop=0  # Loop forever
            )
            return True
            
        return False
        
    def export_selection_as_apng(self, filename):
        if not self.selected_cells or self.sprite_image is None:
            return False
            
        # Extract selected cells as frames
        frames = []
        
        # If using custom frame selection, use the frames in selection order
        if self.is_custom_selecting:
            for col, row in self.custom_frame_selection:
                # Extract the frame
                x = col * self.cell_width
                y = row * self.cell_height
                frame = self.sprite_image.crop(
                    (x, y, x + self.cell_width, y + self.cell_height)
                )
                frames.append(np.array(frame))
        else:
            # Similar logic to the GIF export
            if self.selected_row >= 0:
                row = self.selected_row
                max_cols = self.sprite_image.size[0] // self.cell_width
                
                for col in range(max_cols):
                    x = col * self.cell_width
                    y = row * self.cell_height
                    frame = self.sprite_image.crop(
                        (x, y, x + self.cell_width, y + self.cell_height)
                    )
                    frames.append(np.array(frame))
                
            elif self.selected_column >= 0:
                col = self.selected_column
                max_rows = self.sprite_image.size[1] // self.cell_height
                
                for row in range(max_rows):
                    x = col * self.cell_width
                    y = row * self.cell_height
                    frame = self.sprite_image.crop(
                        (x, y, x + self.cell_width, y + self.cell_height)
                    )
                    frames.append(np.array(frame))
                
            else:
                cells = sorted(self.selected_cells, key=lambda c: (c[1], c[0]))
                
                for col, row in cells:
                    x = col * self.cell_width
                    y = row * self.cell_height
                    frame = self.sprite_image.crop(
                        (x, y, x + self.cell_width, y + self.cell_height)
                    )
                    frames.append(np.array(frame))
        
        # Save frames as APNG
        if frames:
            imageio.mimsave(filename, frames, format='APNG', fps=10)
            return True
            
        return False

    def set_zoom(self, zoom_index):
        if 0 <= zoom_index < len(self.zoom_levels):
            self.current_zoom_index = zoom_index
            self.zoom_factor = self.zoom_levels[zoom_index]
            self.update_pixmap()  # Update with new zoom factor

    def zoom_in(self):
        if self.current_zoom_index < len(self.zoom_levels) - 1:
            self.current_zoom_index += 1
            self.zoom_factor = self.zoom_levels[self.current_zoom_index]
            self.update_pixmap()
            return self.zoom_factor
        return None
        
    def zoom_out(self):
        if self.current_zoom_index > 0:
            self.current_zoom_index -= 1
            self.zoom_factor = self.zoom_levels[self.current_zoom_index]
            self.update_pixmap()
            return self.zoom_factor
        return None
        
    def zoom_reset(self):
        self.current_zoom_index = 0  # Reset to 1x zoom
        self.zoom_factor = self.zoom_levels[self.current_zoom_index]
        self.update_pixmap()
        return self.zoom_factor

    def export_selection_as_png(self, filename):
        """Export the selected area as a PNG image"""
        if not self.selected_cells or self.sprite_image is None:
            return False
            
        # If using custom frame selection, create a strip of selected frames
        if self.is_custom_selecting:
            # Create a new image wide enough for all selected frames
            width = len(self.custom_frame_selection) * self.cell_width
            height = self.cell_height
            new_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            
            # Copy frames in selection order
            for i, (col, row) in enumerate(self.custom_frame_selection):
                # Calculate source and destination coordinates
                src_x = col * self.cell_width
                src_y = row * self.cell_height
                dst_x = i * self.cell_width
                
                # Extract and paste the cell
                cell = self.sprite_image.crop(
                    (src_x, src_y,
                     src_x + self.cell_width,
                     src_y + self.cell_height)
                )
                new_img.paste(cell, (dst_x, 0))
            
            new_img.save(filename)
            return True
            
        # If a row is selected, export the entire row
        if self.selected_row >= 0:
            row = self.selected_row
            # Extract the row
            row_img = self.sprite_image.crop(
                (0, row * self.cell_height,
                 self.sprite_image.size[0], (row + 1) * self.cell_height)
            )
            row_img.save(filename)
            return True
            
        # If a column is selected, export the entire column
        elif self.selected_column >= 0:
            col = self.selected_column
            # Extract the column
            col_img = self.sprite_image.crop(
                (col * self.cell_width, 0,
                 (col + 1) * self.cell_width, self.sprite_image.size[1])
            )
            col_img.save(filename)
            return True
            
        # If multiple cells are selected, create a new image with all selected cells
        else:
            # Calculate the size of the output image
            cells = sorted(self.selected_cells, key=lambda c: (c[1], c[0]))  # Sort by row, then column
            min_col = min(cell[0] for cell in cells)
            max_col = max(cell[0] for cell in cells)
            min_row = min(cell[1] for cell in cells)
            max_row = max(cell[1] for cell in cells)
            
            width = (max_col - min_col + 1) * self.cell_width
            height = (max_row - min_row + 1) * self.cell_height
            
            # Create new image
            new_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            
            # Copy selected cells
            for col, row in cells:
                # Calculate source and destination coordinates
                src_x = col * self.cell_width
                src_y = row * self.cell_height
                dst_x = (col - min_col) * self.cell_width
                dst_y = (row - min_row) * self.cell_height
                
                # Extract and paste the cell
                cell = self.sprite_image.crop(
                    (src_x, src_y,
                     src_x + self.cell_width,
                     src_y + self.cell_height)
                )
                new_img.paste(cell, (dst_x, dst_y))
            
            new_img.save(filename)
            return True
            
        return False


class SpriteToolz(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        # Set window properties
        self.setWindowTitle("Sprite Toolz")
        self.resize(1280, 720)
        self.center_window()
        
        # Create main widget and layout
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        
        # Create sprite canvas
        self.sprite_canvas = SpriteCanvas()
        
        # Create scroll area for the canvas
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidget(self.sprite_canvas)
        self.scroll_area.setWidgetResizable(False)  # Important for proper zooming
        self.scroll_area.setMinimumWidth(800)
        self.scroll_area.setMinimumHeight(600)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center the canvas
        
        # Create tab widget for controls
        tab_widget = QTabWidget()
        tab_widget.setMaximumWidth(300)
        
        # Create basic operations tab
        basic_tab = QWidget()
        basic_layout = QVBoxLayout()
        basic_tab.setLayout(basic_layout)
        
        # File operations group
        file_group = QGroupBox("File Operations")
        file_layout = QVBoxLayout()
        
        self.load_button = QPushButton("Load Sprite Sheet")
        self.load_button.clicked.connect(self.load_spritesheet)
        file_layout.addWidget(self.load_button)
        
        # Export options group
        export_group = QGroupBox("Export Options")
        export_layout = QVBoxLayout()
        
        # Export format selection
        self.export_format_group = QGroupBox("Export Format")
        format_layout = QVBoxLayout()
        
        self.strip_radio = QRadioButton("Sprite Strip")
        self.strip_radio.setChecked(True)
        self.frames_radio = QRadioButton("Individual Frames")
        self.animation_radio = QRadioButton("Animation")
        
        format_layout.addWidget(self.strip_radio)
        format_layout.addWidget(self.frames_radio)
        format_layout.addWidget(self.animation_radio)
        
        self.export_format_group.setLayout(format_layout)
        export_layout.addWidget(self.export_format_group)
        
        self.export_button = QPushButton("Export Selection")
        self.export_button.clicked.connect(self.export_selection)
        self.export_button.setEnabled(False)
        export_layout.addWidget(self.export_button)
        
        export_group.setLayout(export_layout)
        
        file_layout.addWidget(export_group)
        file_group.setLayout(file_layout)
        basic_layout.addWidget(file_group)
        
        # Cell size group
        cell_group = QGroupBox("Cell Size")
        cell_layout = QGridLayout()
        
        # Cell size mode toggle
        self.cell_size_mode_cb = QCheckBox("Use Row/Column Count")
        self.cell_size_mode_cb.stateChanged.connect(self.toggle_cell_size_mode)
        cell_layout.addWidget(self.cell_size_mode_cb, 0, 0, 1, 2)
        
        # Manual cell size widgets
        self.manual_size_widget = QWidget()
        manual_layout = QGridLayout()
        manual_layout.setContentsMargins(0, 0, 0, 0)
        
        manual_layout.addWidget(QLabel("Width:"), 0, 0)
        self.cell_width_spin = QSpinBox()
        self.cell_width_spin.setRange(1, 1000)
        self.cell_width_spin.setValue(32)
        self.cell_width_spin.valueChanged.connect(self.update_cell_size)
        manual_layout.addWidget(self.cell_width_spin, 0, 1)
        
        manual_layout.addWidget(QLabel("Height:"), 1, 0)
        self.cell_height_spin = QSpinBox()
        self.cell_height_spin.setRange(1, 1000)
        self.cell_height_spin.setValue(32)
        self.cell_height_spin.valueChanged.connect(self.update_cell_size)
        manual_layout.addWidget(self.cell_height_spin, 1, 1)
        
        self.manual_size_widget.setLayout(manual_layout)
        cell_layout.addWidget(self.manual_size_widget, 1, 0, 2, 2)
        
        # Row/Column count widgets
        self.count_size_widget = QWidget()
        count_layout = QGridLayout()
        count_layout.setContentsMargins(0, 0, 0, 0)
        
        count_layout.addWidget(QLabel("Rows:"), 0, 0)
        self.row_count_spin = QSpinBox()
        self.row_count_spin.setRange(1, 1000)
        self.row_count_spin.setValue(1)
        self.row_count_spin.valueChanged.connect(self.update_cell_size_from_count)
        count_layout.addWidget(self.row_count_spin, 0, 1)
        
        count_layout.addWidget(QLabel("Columns:"), 1, 0)
        self.col_count_spin = QSpinBox()
        self.col_count_spin.setRange(1, 1000)
        self.col_count_spin.setValue(1)
        self.col_count_spin.valueChanged.connect(self.update_cell_size_from_count)
        count_layout.addWidget(self.col_count_spin, 1, 1)
        
        self.count_size_widget.setLayout(count_layout)
        cell_layout.addWidget(self.count_size_widget, 1, 0, 2, 2)
        self.count_size_widget.hide()  # Initially hidden
        
        # Padding controls
        cell_layout.addWidget(QLabel("Padding:"), 3, 0)
        self.padding_spin = QSpinBox()
        self.padding_spin.setRange(0, 100)
        self.padding_spin.setValue(0)
        self.padding_spin.valueChanged.connect(self.update_padding)
        cell_layout.addWidget(self.padding_spin, 3, 1)
        
        self.apply_padding_button = QPushButton("Apply Padding")
        self.apply_padding_button.clicked.connect(self.apply_padding)
        self.apply_padding_button.setEnabled(False)
        cell_layout.addWidget(self.apply_padding_button, 4, 0, 1, 2)
        
        cell_group.setLayout(cell_layout)
        basic_layout.addWidget(cell_group)
        
        # Grid display group
        grid_group = QGroupBox("Grid")
        grid_layout = QVBoxLayout()
        
        self.show_grid_checkbox = QCheckBox("Show Grid")
        self.show_grid_checkbox.setChecked(True)
        self.show_grid_checkbox.stateChanged.connect(self.toggle_grid)
        
        self.grid_color_button = QPushButton("Grid Color")
        self.grid_color_button.clicked.connect(self.change_grid_color)
        
        grid_layout.addWidget(self.show_grid_checkbox)
        grid_layout.addWidget(self.grid_color_button)
        grid_group.setLayout(grid_layout)
        basic_layout.addWidget(grid_group)
        
        # Zoom group
        zoom_group = QGroupBox("Zoom")
        zoom_layout = QGridLayout()
        
        self.zoom_in_button = QPushButton("Zoom In")
        self.zoom_in_button.clicked.connect(self.zoom_in)
        self.zoom_in_button.setEnabled(False)
        
        self.zoom_out_button = QPushButton("Zoom Out")
        self.zoom_out_button.clicked.connect(self.zoom_out)
        self.zoom_out_button.setEnabled(False)
        
        self.zoom_reset_button = QPushButton("Reset Zoom")
        self.zoom_reset_button.clicked.connect(self.zoom_reset)
        self.zoom_reset_button.setEnabled(False)
        
        self.zoom_label = QLabel("Zoom: 1x")
        
        zoom_layout.addWidget(self.zoom_in_button, 0, 0)
        zoom_layout.addWidget(self.zoom_out_button, 0, 1)
        zoom_layout.addWidget(self.zoom_reset_button, 1, 0, 1, 2)
        zoom_layout.addWidget(self.zoom_label, 2, 0, 1, 2)
        
        zoom_group.setLayout(zoom_layout)
        basic_layout.addWidget(zoom_group)
        
        # Add stretch to push everything to the top
        basic_layout.addStretch()
        
        # Create manipulation tab
        manip_tab = QWidget()
        manip_layout = QVBoxLayout()
        manip_tab.setLayout(manip_layout)
        
        # Selection info
        self.selection_label = QLabel("No selection")
        manip_layout.addWidget(self.selection_label)
        
        # Row operations
        row_ops_group = QGroupBox("Row Operations")
        row_ops_layout = QVBoxLayout()
        
        duplicate_row_btn = QPushButton("Duplicate Row")
        duplicate_row_btn.clicked.connect(self.duplicate_row)
        row_ops_layout.addWidget(duplicate_row_btn)
        
        delete_row_btn = QPushButton("Delete Row")
        delete_row_btn.clicked.connect(self.delete_row)
        row_ops_layout.addWidget(delete_row_btn)
        
        add_row_before_btn = QPushButton("Add Blank Row Before")
        add_row_before_btn.clicked.connect(self.add_row_before)
        row_ops_layout.addWidget(add_row_before_btn)
        
        add_row_after_btn = QPushButton("Add Blank Row After")
        add_row_after_btn.clicked.connect(self.add_row_after)
        row_ops_layout.addWidget(add_row_after_btn)
        
        export_row_btn = QPushButton("Export Row")
        export_row_btn.clicked.connect(self.export_row)
        row_ops_layout.addWidget(export_row_btn)
        
        row_ops_group.setLayout(row_ops_layout)
        manip_layout.addWidget(row_ops_group)
        
        # Column operations
        col_ops_group = QGroupBox("Column Operations")
        col_ops_layout = QVBoxLayout()
        
        duplicate_col_btn = QPushButton("Duplicate Column")
        duplicate_col_btn.clicked.connect(self.duplicate_column)
        col_ops_layout.addWidget(duplicate_col_btn)
        
        delete_col_btn = QPushButton("Delete Column")
        delete_col_btn.clicked.connect(self.delete_column)
        col_ops_layout.addWidget(delete_col_btn)
        
        add_col_before_btn = QPushButton("Add Blank Column Before")
        add_col_before_btn.clicked.connect(self.add_column_before)
        col_ops_layout.addWidget(add_col_before_btn)
        
        add_col_after_btn = QPushButton("Add Blank Column After")
        add_col_after_btn.clicked.connect(self.add_column_after)
        col_ops_layout.addWidget(add_col_after_btn)
        
        export_col_btn = QPushButton("Export Column")
        export_col_btn.clicked.connect(self.export_column)
        col_ops_layout.addWidget(export_col_btn)
        
        col_ops_group.setLayout(col_ops_layout)
        manip_layout.addWidget(col_ops_group)
        
        # Frame operations
        frame_ops_group = QGroupBox("Frame Operations")
        frame_ops_layout = QVBoxLayout()
        
        duplicate_frame_btn = QPushButton("Duplicate Frame")
        duplicate_frame_btn.clicked.connect(self.duplicate_frame)
        frame_ops_layout.addWidget(duplicate_frame_btn)
        
        delete_frame_btn = QPushButton("Delete Frame")
        delete_frame_btn.clicked.connect(self.delete_frame)
        frame_ops_layout.addWidget(delete_frame_btn)
        
        export_frame_btn = QPushButton("Export Frame")
        export_frame_btn.clicked.connect(self.export_frame)
        frame_ops_layout.addWidget(export_frame_btn)
        
        frame_ops_group.setLayout(frame_ops_layout)
        manip_layout.addWidget(frame_ops_group)
        
        # Add stretch to push everything to the top
        manip_layout.addStretch()
        
        # Add tabs to tab widget
        tab_widget.addTab(basic_tab, "Basic")
        tab_widget.addTab(manip_tab, "Manipulate")
        
        # Create batch operations tab
        batch_tab = QWidget()
        batch_layout = QVBoxLayout()
        batch_tab.setLayout(batch_layout)
        
        # Input folder group
        input_group = QGroupBox("Input")
        input_layout = QGridLayout()
        
        self.input_folder_label = QLabel("No folder selected")
        input_layout.addWidget(self.input_folder_label, 0, 0, 1, 2)
        
        select_folder_btn = QPushButton("Select Folder")
        select_folder_btn.clicked.connect(self.select_input_folder)
        input_layout.addWidget(select_folder_btn, 1, 0, 1, 2)
        
        self.include_subfolders_cb = QCheckBox("Process Subfolders")
        input_layout.addWidget(self.include_subfolders_cb, 2, 0, 1, 2)
        
        input_group.setLayout(input_layout)
        batch_layout.addWidget(input_group)
        
        # Batch operations group
        batch_ops_group = QGroupBox("Batch Operations")
        batch_ops_layout = QVBoxLayout()
        
        # Cell size adjustment
        cell_size_layout = QGridLayout()
        cell_size_layout.addWidget(QLabel("Cell Width:"), 0, 0)
        self.batch_cell_width_spin = QSpinBox()
        self.batch_cell_width_spin.setRange(1, 1000)
        self.batch_cell_width_spin.setValue(32)
        cell_size_layout.addWidget(self.batch_cell_width_spin, 0, 1)
        
        cell_size_layout.addWidget(QLabel("Cell Height:"), 1, 0)
        self.batch_cell_height_spin = QSpinBox()
        self.batch_cell_height_spin.setRange(1, 1000)
        self.batch_cell_height_spin.setValue(32)
        cell_size_layout.addWidget(self.batch_cell_height_spin, 1, 1)
        
        cell_size_layout.addWidget(QLabel("Padding:"), 2, 0)
        self.batch_padding_spin = QSpinBox()
        self.batch_padding_spin.setRange(0, 100)
        self.batch_padding_spin.setValue(0)
        cell_size_layout.addWidget(self.batch_padding_spin, 2, 1)
        
        batch_ops_layout.addLayout(cell_size_layout)
        
        # Export options
        self.export_frames_cb = QCheckBox("Export Individual Frames")
        batch_ops_layout.addWidget(self.export_frames_cb)
        
        self.export_rows_cb = QCheckBox("Export Rows as Strips")
        batch_ops_layout.addWidget(self.export_rows_cb)
        
        self.export_gif_cb = QCheckBox("Export Rows as GIF")
        batch_ops_layout.addWidget(self.export_gif_cb)
        
        self.export_apng_cb = QCheckBox("Export Rows as APNG")
        batch_ops_layout.addWidget(self.export_apng_cb)
        
        # Process button
        self.process_batch_btn = QPushButton("Process Folder")
        self.process_batch_btn.clicked.connect(self.process_batch)
        self.process_batch_btn.setEnabled(False)
        batch_ops_layout.addWidget(self.process_batch_btn)
        
        batch_ops_group.setLayout(batch_ops_layout)
        batch_layout.addWidget(batch_ops_group)
        
        # Progress group
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout()
        
        self.batch_progress_label = QLabel("Ready")
        progress_layout.addWidget(self.batch_progress_label)
        
        progress_group.setLayout(progress_layout)
        batch_layout.addWidget(progress_group)
        
        # Add stretch to push everything to the top
        batch_layout.addStretch()
        
        # Add batch tab
        tab_widget.addTab(batch_tab, "Batch")
        
        # Add widgets to main layout
        main_layout.addWidget(self.scroll_area)
        main_layout.addWidget(tab_widget)
        
        # Add status bar
        self.statusBar().showMessage("Ready")
        
    def center_window(self):
        # Center the window on the screen
        screen_geometry = QApplication.primaryScreen().geometry()
        x = (screen_geometry.width() - self.width()) // 2
        y = (screen_geometry.height() - self.height()) // 2
        self.move(x, y)
    
    def load_spritesheet(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Open Sprite Sheet", "", "Image Files (*.png *.jpg *.bmp *.gif)"
        )
        
        if filename:
            self.sprite_canvas.load_spritesheet(filename)
            self.export_button.setEnabled(True)
            # Enable zoom buttons
            self.zoom_in_button.setEnabled(True)
            self.zoom_out_button.setEnabled(True)
            self.zoom_reset_button.setEnabled(True)
            self.statusBar().showMessage(f"Loaded: {filename}")
    
    def export_selection(self):
        if self.sprite_canvas.sprite_image is None or not self.sprite_canvas.selected_cells:
            QMessageBox.warning(self, "No Selection", "Please select cells to export.")
            return
            
        # Determine export format based on radio button selection
        if self.strip_radio.isChecked():
            # Export as sprite strip
            filename, _ = QFileDialog.getSaveFileName(
                self, "Save Selection", "", "PNG Files (*.png)"
            )
            if filename:
                success = self.sprite_canvas.export_selection_as_png(filename)
                if success:
                    self.statusBar().showMessage(f"Exported sprite strip to: {filename}")
                else:
                    QMessageBox.warning(self, "Export Failed", "Failed to export the sprite strip.")
                    
        elif self.frames_radio.isChecked():
            # Export as individual frames
            directory = QFileDialog.getExistingDirectory(
                self, "Select Export Directory", "",
                QFileDialog.Option.ShowDirsOnly
            )
            if directory:
                success = self.export_individual_frames(directory)
                if success:
                    self.statusBar().showMessage(f"Exported individual frames to: {directory}")
                else:
                    QMessageBox.warning(self, "Export Failed", "Failed to export individual frames.")
                    
        else:  # Animation radio is checked
            # Get file name for saving animation
            filename, filter_used = QFileDialog.getSaveFileName(
                self, "Save Animation", "", "GIF (*.gif);;PNG (*.png)"
            )
            if filename:
                success = False
                if filter_used == "GIF (*.gif)":
                    success = self.sprite_canvas.export_selection_as_gif(filename)
                else:  # PNG (APNG)
                    success = self.sprite_canvas.export_selection_as_apng(filename)
                    
                if success:
                    self.statusBar().showMessage(f"Exported animation to: {filename}")
                else:
                    QMessageBox.warning(self, "Export Failed", "Failed to export the animation.")
                    
    def export_individual_frames(self, directory):
        """Export selected frames as individual PNG files"""
        try:
            if self.sprite_canvas.is_custom_selecting:
                # Export frames in selection order
                for i, (col, row) in enumerate(self.sprite_canvas.custom_frame_selection):
                    # Extract the frame
                    x = col * self.sprite_canvas.cell_width
                    y = row * self.sprite_canvas.cell_height
                    frame = self.sprite_canvas.sprite_image.crop(
                        (x, y,
                         x + self.sprite_canvas.cell_width,
                         y + self.sprite_canvas.cell_height)
                    )
                    # Save frame
                    frame_path = os.path.join(directory, f"frame_{i:03d}.png")
                    frame.save(frame_path)
            else:
                # Handle regular selection (row, column, or area)
                cells = sorted(self.sprite_canvas.selected_cells, key=lambda c: (c[1], c[0]))
                for i, (col, row) in enumerate(cells):
                    # Extract the frame
                    x = col * self.sprite_canvas.cell_width
                    y = row * self.sprite_canvas.cell_height
                    frame = self.sprite_canvas.sprite_image.crop(
                        (x, y,
                         x + self.sprite_canvas.cell_width,
                         y + self.sprite_canvas.cell_height)
                    )
                    # Save frame
                    frame_path = os.path.join(directory, f"frame_{i:03d}.png")
                    frame.save(frame_path)
            return True
        except Exception as e:
            self.statusBar().showMessage(f"Error exporting frames: {str(e)}")
            return False

    def toggle_cell_size_mode(self, state):
        """Toggle between manual cell size and row/column count mode"""
        if state == Qt.CheckState.Checked.value:
            self.manual_size_widget.hide()
            self.count_size_widget.show()
            self.update_cell_size_from_count()
        else:
            self.manual_size_widget.show()
            self.count_size_widget.hide()
            self.update_cell_size()
            
    def update_cell_size_from_count(self):
        """Update cell size based on row and column counts"""
        if not self.sprite_canvas.sprite_image:
            return
            
        img_width = self.sprite_canvas.sprite_image.size[0]
        img_height = self.sprite_canvas.sprite_image.size[1]
        
        cols = self.col_count_spin.value()
        rows = self.row_count_spin.value()
        
        if cols > 0 and rows > 0:
            # Calculate cell size based on image dimensions and row/column counts
            cell_width = img_width // cols
            cell_height = img_height // rows
            
            # Update the manual spinboxes (without triggering their signals)
            self.cell_width_spin.blockSignals(True)
            self.cell_height_spin.blockSignals(True)
            
            self.cell_width_spin.setValue(cell_width)
            self.cell_height_spin.setValue(cell_height)
            
            self.cell_width_spin.blockSignals(False)
            self.cell_height_spin.blockSignals(False)
            
            # Update the canvas
            self.sprite_canvas.cell_width = cell_width
            self.sprite_canvas.cell_height = cell_height
            self.sprite_canvas.update()
            
    def update_cell_size(self):
        """Update cell size based on manual width/height values"""
        if not self.sprite_canvas.sprite_image:
            return
            
        width = self.cell_width_spin.value()
        height = self.cell_height_spin.value()
        
        if width > 0 and height > 0:
            # Calculate row/column counts based on cell size
            img_width = self.sprite_canvas.sprite_image.size[0]
            img_height = self.sprite_canvas.sprite_image.size[1]
            
            cols = img_width // width
            rows = img_height // height
            
            # Update the count spinboxes (without triggering their signals)
            self.row_count_spin.blockSignals(True)
            self.col_count_spin.blockSignals(True)
            
            self.row_count_spin.setValue(rows)
            self.col_count_spin.setValue(cols)
            
            self.row_count_spin.blockSignals(False)
            self.col_count_spin.blockSignals(False)
            
            # Update the canvas
            self.sprite_canvas.cell_width = width
            self.sprite_canvas.cell_height = height
            self.sprite_canvas.update()
    
    def update_padding(self):
        padding = self.padding_spin.value()
        self.sprite_canvas.set_padding(padding)
        
    def apply_padding(self):
        padding = self.padding_spin.value()
        if padding > 0:
            self.sprite_canvas.apply_padding()
            self.cell_width_spin.setValue(self.sprite_canvas.cell_width)
            self.cell_height_spin.setValue(self.sprite_canvas.cell_height)
            self.padding_spin.setValue(0)
            self.statusBar().showMessage(f"Applied padding: {padding} pixels")
        else:
            self.statusBar().showMessage("No padding to apply")
    
    def toggle_grid(self, state):
        """Toggle grid visibility in the sprite canvas"""
        self.sprite_canvas.set_grid_visible(state == Qt.CheckState.Checked.value)
        self.statusBar().showMessage("Grid " + ("shown" if state == Qt.CheckState.Checked.value else "hidden"))

    def change_grid_color(self):
        color = QColorDialog.getColor(self.sprite_canvas.grid_color, self)
        if color.isValid():
            self.sprite_canvas.set_grid_color(color)
    
    def duplicate_row(self):
        """Duplicate the selected row"""
        if not self.sprite_canvas.sprite_image or not self.sprite_canvas.selection_start:
            return
            
        row = self.sprite_canvas.selection_start[1] // self.sprite_canvas.cell_height
        img = self.sprite_canvas.sprite_image
        height = self.sprite_canvas.cell_height
        
        # Create new image with extra row
        new_height = img.size[1] + height
        new_img = Image.new('RGBA', (img.size[0], new_height), (0, 0, 0, 0))
        
        # Copy original image
        new_img.paste(img, (0, 0))
        
        # Copy selected row to new position
        row_img = img.crop((0, row * height, img.size[0], (row + 1) * height))
        new_img.paste(row_img, (0, img.size[1]))
        
        # Update the sprite image
        self.sprite_canvas.sprite_image = new_img
        self.sprite_canvas.update_pixmap()
        self.statusBar().showMessage(f"Duplicated row {row}")

    def delete_row(self):
        """Delete the selected row"""
        if not self.sprite_canvas.sprite_image or not self.sprite_canvas.selection_start:
            return
            
        row = self.sprite_canvas.selection_start[1] // self.sprite_canvas.cell_height
        img = self.sprite_canvas.sprite_image
        height = self.sprite_canvas.cell_height
        
        # Create new image without the selected row
        new_height = img.size[1] - height
        new_img = Image.new('RGBA', (img.size[0], new_height), (0, 0, 0, 0))
        
        # Copy parts before and after the selected row
        if row > 0:
            new_img.paste(img.crop((0, 0, img.size[0], row * height)), (0, 0))
        if row < (img.size[1] // height - 1):
            new_img.paste(img.crop((0, (row + 1) * height, img.size[0], img.size[1])), 
                         (0, row * height))
        
        # Update the sprite image
        self.sprite_canvas.sprite_image = new_img
        self.sprite_canvas.update_pixmap()
        self.statusBar().showMessage(f"Deleted row {row}")

    def add_row_before(self):
        """Add a blank row before the selected row"""
        if not self.sprite_canvas.sprite_image or not self.sprite_canvas.selection_start:
            return
            
        row = self.sprite_canvas.selection_start[1] // self.sprite_canvas.cell_height
        img = self.sprite_canvas.sprite_image
        height = self.sprite_canvas.cell_height
        
        # Create new image with extra row
        new_height = img.size[1] + height
        new_img = Image.new('RGBA', (img.size[0], new_height), (0, 0, 0, 0))
        
        # Copy parts before and after the insertion point
        if row > 0:
            new_img.paste(img.crop((0, 0, img.size[0], row * height)), (0, 0))
        new_img.paste(img.crop((0, row * height, img.size[0], img.size[1])), 
                     (0, (row + 1) * height))
        
        # Update the sprite image
        self.sprite_canvas.sprite_image = new_img
        self.sprite_canvas.update_pixmap()
        self.statusBar().showMessage(f"Added blank row before row {row}")

    def add_row_after(self):
        """Add a blank row after the selected row"""
        if not self.sprite_canvas.sprite_image or not self.sprite_canvas.selection_start:
            return
            
        row = self.sprite_canvas.selection_start[1] // self.sprite_canvas.cell_height
        img = self.sprite_canvas.sprite_image
        height = self.sprite_canvas.cell_height
        
        # Create new image with extra row
        new_height = img.size[1] + height
        new_img = Image.new('RGBA', (img.size[0], new_height), (0, 0, 0, 0))
        
        # Copy parts before and after the insertion point
        new_img.paste(img.crop((0, 0, img.size[0], (row + 1) * height)), (0, 0))
        if row < (img.size[1] // height - 1):
            new_img.paste(img.crop((0, (row + 1) * height, img.size[0], img.size[1])), 
                         ((row + 2) * height))
        
        # Update the sprite image
        self.sprite_canvas.sprite_image = new_img
        self.sprite_canvas.update_pixmap()
        self.statusBar().showMessage(f"Added blank row after row {row}")

    def export_row(self):
        """Export the selected row as a new sprite sheet"""
        if not self.sprite_canvas.sprite_image or not self.sprite_canvas.selection_start:
            return
            
        row = self.sprite_canvas.selection_start[1] // self.sprite_canvas.cell_height
        img = self.sprite_canvas.sprite_image
        height = self.sprite_canvas.cell_height
        
        # Extract the row
        row_img = img.crop((0, row * height, img.size[0], (row + 1) * height))
        
        # Get save filename
        filename, _ = QFileDialog.getSaveFileName(self, "Save Row",
                                                "", "PNG Files (*.png);;All Files (*)")
        if filename:
            row_img.save(filename)
            self.statusBar().showMessage(f"Row exported to {filename}")

    def duplicate_column(self):
        """Duplicate the selected column"""
        if not self.sprite_canvas.sprite_image or not self.sprite_canvas.selection_start:
            return
            
        col = self.sprite_canvas.selection_start[0] // self.sprite_canvas.cell_width
        img = self.sprite_canvas.sprite_image
        width = self.sprite_canvas.cell_width
        
        # Create new image with extra column
        new_width = img.size[0] + width
        new_img = Image.new('RGBA', (new_width, img.size[1]), (0, 0, 0, 0))
        
        # Copy original image
        new_img.paste(img, (0, 0))
        
        # Copy selected column to new position
        col_img = img.crop((col * width, 0, (col + 1) * width, img.size[1]))
        new_img.paste(col_img, (img.size[0], 0))
        
        # Update the sprite image
        self.sprite_canvas.sprite_image = new_img
        self.sprite_canvas.update_pixmap()
        self.statusBar().showMessage(f"Duplicated column {col}")

    def delete_column(self):
        """Delete the selected column"""
        if not self.sprite_canvas.sprite_image or not self.sprite_canvas.selection_start:
            return
            
        col = self.sprite_canvas.selection_start[0] // self.sprite_canvas.cell_width
        img = self.sprite_canvas.sprite_image
        width = self.sprite_canvas.cell_width
        
        # Create new image without the selected column
        new_width = img.size[0] - width
        new_height = img.size[1]
        new_img = Image.new('RGBA', (new_width, new_height), (0, 0, 0, 0))
        
        # Copy parts before and after the selected column
        if col > 0:
            new_img.paste(img.crop((0, 0, col * width, img.size[1])), (0, 0))
        if col < (img.size[0] // width - 1):
            new_img.paste(img.crop(((col + 1) * width, 0, img.size[0], img.size[1])), 
                         (col * width, 0))
        
        # Update the sprite image
        self.sprite_canvas.sprite_image = new_img
        self.sprite_canvas.update_pixmap()
        self.statusBar().showMessage(f"Deleted column {col}")

    def add_column_before(self):
        """Add a blank column before the selected column"""
        if not self.sprite_canvas.sprite_image or not self.sprite_canvas.selection_start:
            return
            
        col = self.sprite_canvas.selection_start[0] // self.sprite_canvas.cell_width
        img = self.sprite_canvas.sprite_image
        width = self.sprite_canvas.cell_width
        
        # Create new image with extra column
        new_width = img.size[0] + width
        new_img = Image.new('RGBA', (new_width, img.size[1]), (0, 0, 0, 0))
        
        # Copy parts before and after the insertion point
        if col > 0:
            new_img.paste(img.crop((0, 0, col * width, img.size[1])), (0, 0))
        new_img.paste(img.crop((col * width, 0, img.size[0], img.size[1])), 
                     ((col + 1) * width, 0))
        
        # Update the sprite image
        self.sprite_canvas.sprite_image = new_img
        self.sprite_canvas.update_pixmap()
        self.statusBar().showMessage(f"Added blank column before column {col}")

    def add_column_after(self):
        """Add a blank column after the selected column"""
        if not self.sprite_canvas.sprite_image or not self.sprite_canvas.selection_start:
            return
            
        col = self.sprite_canvas.selection_start[0] // self.sprite_canvas.cell_width
        img = self.sprite_canvas.sprite_image
        width = self.sprite_canvas.cell_width
        
        # Create new image with extra column
        new_width = img.size[0] + width
        new_img = Image.new('RGBA', (new_width, img.size[1]), (0, 0, 0, 0))
        
        # Copy parts before and after the insertion point
        new_img.paste(img.crop((0, 0, (col + 1) * width, img.size[1])), (0, 0))
        if col < (img.size[0] // width - 1):
            new_img.paste(img.crop(((col + 1) * width, 0, img.size[0], img.size[1])), 
                         ((col + 2) * width, 0))
        
        # Update the sprite image
        self.sprite_canvas.sprite_image = new_img
        self.sprite_canvas.update_pixmap()
        self.statusBar().showMessage(f"Added blank column after column {col}")

    def export_column(self):
        """Export the selected column as a new sprite sheet"""
        if not self.sprite_canvas.sprite_image or not self.sprite_canvas.selection_start:
            return
            
        col = self.sprite_canvas.selection_start[0] // self.sprite_canvas.cell_width
        img = self.sprite_canvas.sprite_image
        width = self.sprite_canvas.cell_width
        
        # Extract the column
        col_img = img.crop((col * width, 0, (col + 1) * width, img.size[1]))
        
        # Get save filename
        filename, _ = QFileDialog.getSaveFileName(self, "Save Column",
                                                "", "PNG Files (*.png);;All Files (*)")
        if filename:
            col_img.save(filename)
            self.statusBar().showMessage(f"Column exported to {filename}")

    def duplicate_frame(self):
        """Duplicate the selected frame"""
        if not self.sprite_canvas.sprite_image or not self.sprite_canvas.selection_start:
            return
            
        col = self.sprite_canvas.selection_start[0] // self.sprite_canvas.cell_width
        row = self.sprite_canvas.selection_start[1] // self.sprite_canvas.cell_height
        img = self.sprite_canvas.sprite_image
        width = self.sprite_canvas.cell_width
        height = self.sprite_canvas.cell_height
        
        # Extract the frame
        frame = img.crop((col * width, row * height, (col + 1) * width, (row + 1) * height))
        
        # Create new image with space for the duplicated frame
        new_width = img.size[0] + width
        new_img = Image.new('RGBA', (new_width, img.size[1]), (0, 0, 0, 0))
        
        # Copy original image
        new_img.paste(img, (0, 0))
        
        # Add duplicated frame at the end of the row
        new_img.paste(frame, (img.size[0], row * height))
        
        # Update the sprite image
        self.sprite_canvas.sprite_image = new_img
        self.sprite_canvas.update_pixmap()
        self.statusBar().showMessage(f"Duplicated frame at ({col}, {row})")

    def delete_frame(self):
        """Delete the selected frame"""
        if not self.sprite_canvas.sprite_image or not self.sprite_canvas.selection_start:
            return
            
        col = self.sprite_canvas.selection_start[0] // self.sprite_canvas.cell_width
        row = self.sprite_canvas.selection_start[1] // self.sprite_canvas.cell_height
        img = self.sprite_canvas.sprite_image
        width = self.sprite_canvas.cell_width
        height = self.sprite_canvas.cell_height
        
        # Create new image without the selected frame
        new_width = img.size[0] - width
        new_img = Image.new('RGBA', (new_width, img.size[1]), (0, 0, 0, 0))
        
        # Copy all frames except the selected one
        if col > 0:
            new_img.paste(img.crop((0, 0, col * width, img.size[1])), (0, 0))
        if col < (img.size[0] // width - 1):
            new_img.paste(img.crop(((col + 1) * width, 0, img.size[0], img.size[1])), 
                         (col * width, 0))
        
        # Update the sprite image
        self.sprite_canvas.sprite_image = new_img
        self.sprite_canvas.update_pixmap()
        self.statusBar().showMessage(f"Deleted frame at ({col}, {row})")

    def export_frame(self):
        """Export the selected frame as an individual image file"""
        if not self.sprite_canvas.sprite_image or not self.sprite_canvas.selection_start:
            return
            
        col = self.sprite_canvas.selection_start[0] // self.sprite_canvas.cell_width
        row = self.sprite_canvas.selection_start[1] // self.sprite_canvas.cell_height
        img = self.sprite_canvas.sprite_image
        width = self.sprite_canvas.cell_width
        height = self.sprite_canvas.cell_height
        
        # Extract the frame
        frame = img.crop((col * width, row * height, (col + 1) * width, (row + 1) * height))
        
        # Get save filename
        filename, _ = QFileDialog.getSaveFileName(self, "Save Frame",
                                                "", "PNG Files (*.png);;All Files (*)")
        if filename:
            frame.save(filename)
            self.statusBar().showMessage(f"Frame exported to {filename}")

    def zoom_in(self):
        """Handle zoom in button click"""
        new_zoom = self.sprite_canvas.zoom_in()
        if new_zoom:
            self.zoom_label.setText(f"Zoom: {int(new_zoom)}x")
            # Update scroll area to adjust scroll bars
            self.scroll_area.setWidgetResizable(False)
            self.scroll_area.updateGeometry()
            self.statusBar().showMessage(f"Zoomed in to {int(new_zoom)}x")

    def zoom_out(self):
        """Handle zoom out button click"""
        new_zoom = self.sprite_canvas.zoom_out()
        if new_zoom:
            self.zoom_label.setText(f"Zoom: {int(new_zoom)}x")
            # Update scroll area to adjust scroll bars
            self.scroll_area.setWidgetResizable(False)
            self.scroll_area.updateGeometry()
            self.statusBar().showMessage(f"Zoomed out to {int(new_zoom)}x")

    def zoom_reset(self):
        """Handle zoom reset button click"""
        new_zoom = self.sprite_canvas.zoom_reset()
        self.zoom_label.setText(f"Zoom: {int(new_zoom)}x")
        # Update scroll area to adjust scroll bars
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.updateGeometry()
        self.statusBar().showMessage("Zoom reset to 1x")

    def update_button_states(self):
        """Update the enabled/disabled state of manipulation buttons based on selection"""
        has_image = self.sprite_canvas.sprite_image is not None
        has_selection = self.sprite_canvas.selection_start is not None and self.sprite_canvas.selection_end is not None
        
        # Find all manipulation buttons and update their states
        for group in self.findChildren(QGroupBox):
            if group.title() in ["Row Operations", "Column Operations", "Frame Operations"]:
                for button in group.findChildren(QPushButton):
                    button.setEnabled(has_image and has_selection)

    def update_selection_label(self):
        """Update the selection info label"""
        if not self.sprite_canvas.sprite_image or not self.sprite_canvas.selection_start:
            self.selection_label.setText("No selection")
            return
            
        start_row = self.sprite_canvas.selection_start[1] // self.sprite_canvas.cell_height
        end_row = self.sprite_canvas.selection_end[1] // self.sprite_canvas.cell_height
        start_col = self.sprite_canvas.selection_start[0] // self.sprite_canvas.cell_width
        end_col = self.sprite_canvas.selection_end[0] // self.sprite_canvas.cell_width
        
        if start_row == end_row and start_col == end_col:
            self.selection_label.setText(f"Selected frame: ({start_col}, {start_row})")
        elif start_row == end_row:
            self.selection_label.setText(f"Selected row: {start_row}")
        elif start_col == end_col:
            self.selection_label.setText(f"Selected column: {start_col}")
        else:
            self.selection_label.setText(f"Selected area: ({start_col}, {start_row}) to ({end_col}, {end_row})")

    def select_input_folder(self):
        """Open folder selection dialog for batch processing"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Input Folder",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder:
            self.input_folder_label.setText(folder)
            self.process_batch_btn.setEnabled(True)
            self.statusBar().showMessage(f"Selected folder: {folder}")
            
    def process_batch(self):
        """Process all sprite sheets in the selected folder"""
        input_folder = self.input_folder_label.text()
        if input_folder == "No folder selected":
            return
            
        # Get processing options
        cell_width = self.batch_cell_width_spin.value()
        cell_height = self.batch_cell_height_spin.value()
        padding = self.batch_padding_spin.value()
        export_frames = self.export_frames_cb.isChecked()
        export_rows = self.export_rows_cb.isChecked()
        export_gif = self.export_gif_cb.isChecked()
        export_apng = self.export_apng_cb.isChecked()
        include_subfolders = self.include_subfolders_cb.isChecked()
        
        # Create output folder
        output_folder = os.path.join(input_folder, "processed")
        os.makedirs(output_folder, exist_ok=True)
        
        # Get list of files to process
        if include_subfolders:
            sprite_files = []
            for root, _, files in os.walk(input_folder):
                for file in files:
                    if file.lower().endswith(('.png', '.jpg', '.bmp', '.gif')):
                        sprite_files.append(os.path.join(root, file))
        else:
            sprite_files = [
                os.path.join(input_folder, f) for f in os.listdir(input_folder)
                if f.lower().endswith(('.png', '.jpg', '.bmp', '.gif'))
            ]
        
        if not sprite_files:
            self.batch_progress_label.setText("No sprite sheets found")
            return
            
        # Process each file
        total_files = len(sprite_files)
        for i, file_path in enumerate(sprite_files, 1):
            self.batch_progress_label.setText(f"Processing {i}/{total_files}: {os.path.basename(file_path)}")
            self.statusBar().showMessage(f"Processing {os.path.basename(file_path)}")
            QApplication.processEvents()  # Update UI
            
            try:
                # Load sprite sheet
                img = Image.open(file_path)
                
                # Apply padding if needed
                if padding > 0:
                    # Calculate cells
                    cols = img.size[0] // cell_width
                    rows = img.size[1] // cell_height
                    
                    # Create padded image
                    padded_width = cols * (cell_width + 2 * padding)
                    padded_height = rows * (cell_height + 2 * padding)
                    padded_img = Image.new(img.mode, (padded_width, padded_height), (0, 0, 0, 0))
                    
                    # Copy cells with padding
                    for row in range(rows):
                        for col in range(cols):
                            src_x = col * cell_width
                            src_y = row * cell_height
                            dst_x = col * (cell_width + 2 * padding) + padding
                            dst_y = row * (cell_height + 2 * padding) + padding
                            
                            cell = img.crop(
                                (src_x, src_y, src_x + cell_width, src_y + cell_height)
                            )
                            padded_img.paste(cell, (dst_x, dst_y))
                            
                    img = padded_img
                    cell_width += 2 * padding
                    cell_height += 2 * padding
                
                # Create output subfolder matching input structure
                rel_path = os.path.relpath(os.path.dirname(file_path), input_folder)
                curr_output_folder = os.path.join(output_folder, rel_path)
                os.makedirs(curr_output_folder, exist_ok=True)
                
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                
                # Export individual frames if requested
                if export_frames:
                    frames_folder = os.path.join(curr_output_folder, f"{base_name}_frames")
                    os.makedirs(frames_folder, exist_ok=True)
                    
                    cols = img.size[0] // cell_width
                    rows = img.size[1] // cell_height
                    frame_count = 0
                    
                    for row in range(rows):
                        for col in range(cols):
                            frame = img.crop(
                                (col * cell_width, row * cell_height,
                                 (col + 1) * cell_width, (row + 1) * cell_height))
                            frame.save(os.path.join(frames_folder, f"frame_{frame_count:03d}.png"))
                            frame_count += 1
                
                # Export rows if requested
                if export_rows or export_gif or export_apng:
                    rows_folder = os.path.join(curr_output_folder, f"{base_name}_rows")
                    os.makedirs(rows_folder, exist_ok=True)
                    
                    rows = img.size[1] // cell_height
                    cols = img.size[0] // cell_width
                    
                    for row in range(rows):
                        # Export row as strip if requested
                        if export_rows:
                            row_img = img.crop(
                                (0, row * cell_height,
                                 img.size[0], (row + 1) * cell_height))
                            row_img.save(os.path.join(rows_folder, f"row_{row:03d}.png"))
                        
                        # Export as GIF if requested
                        if export_gif:
                            frames = []
                            for col in range(cols):
                                frame = img.crop(
                                    (col * cell_width, row * cell_height,
                                     (col + 1) * cell_width, (row + 1) * cell_height))
                                # Convert frame to RGBA if it isn't already
                                if frame.mode != 'RGBA':
                                    frame = frame.convert('RGBA')
                                frames.append(frame)
                            
                            if frames:
                                try:
                                    gif_path = os.path.join(rows_folder, f"row_{row:03d}.gif")
                                    frames[0].save(
                                        gif_path,
                                        format='GIF',
                                        append_images=frames[1:],
                                        save_all=True,
                                        duration=100,
                                        loop=0,
                                        transparency=0,
                                        disposal=2  # Clear previous frame
                                    )
                                    self.statusBar().showMessage(f"Created GIF: {os.path.basename(gif_path)}")
                                except Exception as e:
                                    self.statusBar().showMessage(f"Error creating GIF for row {row}: {str(e)}")
                        
                        # Export as APNG if requested
                        if export_apng:
                            frames = []
                            for col in range(cols):
                                frame = img.crop(
                                    (col * cell_width, row * cell_height,
                                     (col + 1) * cell_width, (row + 1) * cell_height))
                                # Convert frame to RGBA if it isn't already
                                if frame.mode != 'RGBA':
                                    frame = frame.convert('RGBA')
                                frames.append(np.array(frame))
                            
                            if frames:
                                try:
                                    apng_path = os.path.join(rows_folder, f"row_{row:03d}.png")
                                    # Save as animated PNG with proper animation settings
                                    imageio.mimsave(
                                        apng_path,
                                        frames,
                                        format='APNG',
                                        fps=10,  # 10 frames per second
                                        loop=0,  # Loop forever
                                        duration=100  # 100ms per frame
                                    )
                                    self.statusBar().showMessage(f"Created animated PNG for row {row}")
                                except Exception as e:
                                    self.statusBar().showMessage(f"Error creating animated PNG for row {row}: {str(e)}")
                                    continue
                
            except Exception as e:
                error_msg = f"Error processing {os.path.basename(file_path)}: {str(e)}"
                self.statusBar().showMessage(error_msg)
                self.batch_progress_label.setText(error_msg)
                continue
        
        self.batch_progress_label.setText("Processing complete")
        self.statusBar().showMessage("Batch processing complete")


def main():
    app = QApplication(sys.argv)
    window = SpriteToolz()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main() 